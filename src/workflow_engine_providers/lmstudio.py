"""The `lmstudio` adapter: the chat call of a protocol, plus the residency of one product.

It is a subclass rather than a set of options on `openai_compatible`, and that is the whole design.
The parent is named after a protocol no vendor owns, so a load-and-unload option inside it would be
dead on every other server an installation might point it at, and a node asking for a release would
silently do nothing. Here the endpoints exist, so the option means what it says.

This is also the adapter the provider seat was built for. ADR 014 §2 made an adapter a class because
one speaking to a local server has to remember what that server is holding for it; everything below
is that memory, and the rules it lives by: it starts empty, it is re-checked against the server
before anything is released, and the server is right whenever the two disagree.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, ClassVar

from workflow_engine.exceptions import WorkflowRuntimeError
from workflow_engine.providers.base_provider import (
    FinalizeReason,
    ProviderCall,
    ProviderErrorClass,
    ProviderReply,
    ProviderSettings,
)
from workflow_engine.registry.provider_registry import (
    ProviderOperatorMetadata,
    ProviderOptionDoc,
    register_provider,
)
from workflow_engine_providers.openai_compatible import (
    OpenAICompatibleProvider,
    classify_status,
    text_of,
)

ADAPTER_NAME = "lmstudio"

NATIVE_API_PATH = "api/v1"
OPENAI_ROOT_SUFFIX = "/v1"

# Relative to the native API root, which already carries NATIVE_API_PATH.
MODELS_PATH = "models"
LOAD_PATH = f"{MODELS_PATH}/load"
UNLOAD_PATH = f"{MODELS_PATH}/unload"

DEFAULT_LOAD_TIMEOUT_SECONDS = 600.0

API_BASE_URL_OPTION = "api_base_url"
LOAD_TIMEOUT_OPTION = "load_timeout"
LOAD_CONFIG_OPTION = "load_config"
"""What a model is loaded with, declared once in the provider block.

Its members are the server's vocabulary rather than this adapter's - a context length, an
attention setting, whatever the product adds next - so a setting the server gains later needs no
release here. The name is the server's own: it is what a load echoes back under
'echo_load_config'.
"""
RELEASE_FOREIGN_OPTION = "release_foreign"
RELEASE_OPTION = "release"

LOAD_FAILED_TYPE = "model_load_failed"
"""The one error type the load endpoint uses for everything that went wrong while loading.

It carries no distinction the adapter could act on, and the wording underneath it carries none
reliably either. A machine too small for the model was measured refusing in two different ways: once
predicted before any allocation, in a sentence that names the memory it would have needed, and once
discovered during the allocation itself, as nothing but "Failed to load model" after nearly a minute
of trying. Both are the same recoverable condition. Since the second says nothing, a rule reading the
first would call it permanent - so the load failure keeps the class its status gives it, which is
transient, and a load that can never succeed is retried a few times before the node gives up. That
is the cheaper mistake of the two available. See the session note of `2026-08-25-implementation-1`.
"""

INSTANCE_ID_KEY = "instance_id"
"""How the load answer and the unload request name an instance."""

LISTED_INSTANCE_ID_KEY = "id"
"""How the model listing names the same thing. The two differ in the server's API, not here."""
KEEP_LOADED_ON = (FinalizeReason.PAUSED,)
"""The one outcome that keeps a model resident: an answer is expected shortly, so a release would
only be followed by a reload a minute later. Every other outcome ends the run. See ADR 014 §2."""


class LmStudioResidencyError(WorkflowRuntimeError):
    """A model this adapter loaded could not be released when the run ended.

    Raised out of ``finalize`` on purpose: that is the channel by which the seat reports a failure
    to release on the response of the run, and the seat is what guarantees it changes neither the
    outcome nor the exit code. A model left resident is an operator's problem, never a failed
    workflow. See ADR 014 §2.
    """


@register_provider(
    description="Calls a local LM Studio server and manages which model it keeps resident.",
    provider_type=ADAPTER_NAME,
    notes=[
        "Everything about the call itself - the request, the reply, the six error classes - is the "
        "'openai_compatible' adapter's; this one adds only what LM Studio offers beyond the "
        "protocol, which is loading and unloading a model.",
        "The model of a call is loaded before the call when the server does not already hold it, so "
        "the adapter knows which resident instance is its own.",
        "A model the adapter did not load - one loaded from the application, or by another process - "
        f"is never unloaded, unless the provider block sets '{RELEASE_FOREIGN_OPTION}'. A run does "
        "not evict what it did not put there.",
        "What a model is loaded with is declared once in the provider block and reaches the server "
        "unread. It applies to a load the adapter performs; a model the server already holds is used "
        "as it stands, whatever window it was loaded with.",
        "What the adapter remembers about the server is a cache of a fact outside this process: it "
        "is re-checked before anything is released, and the server is right when the two disagree.",
        "A model left resident is never a failed workflow. A release that fails is reported on the "
        "response of the run and changes neither its outcome nor its exit code.",
    ],
    metadata=ProviderOperatorMetadata(
        description=(
            "Speaks the OpenAI-compatible chat protocol of a local LM Studio server and, beside it, "
            "the server's own model API. Before a call it asks the server which instances are "
            "loaded and loads the model if none is; after a call it releases the instance when the "
            "node asked for it; when the run ends it releases what it loaded, unless the run only "
            "paused, where the next call is expected shortly. It releases only instances it loaded "
            "itself unless the provider block widens that."
        ),
        call_options={
            RELEASE_OPTION: ProviderOptionDoc(
                type="boolean",
                description=(
                    "Release the model right after this call rather than at the end of the run. Use "
                    "it on the last call of a long branch, or before a step that needs the memory "
                    "for something else. A release that fails does not fail the node."
                ),
            ),
        },
        configuration_keys=(
            "adapter",
            "base_url",
            "model",
            API_BASE_URL_OPTION,
            LOAD_TIMEOUT_OPTION,
            LOAD_CONFIG_OPTION,
            RELEASE_FOREIGN_OPTION,
        ),
    ),
)
class LmStudioProvider(OpenAICompatibleProvider):
    """An LM Studio adapter that owns the models it loads and releases them when the run is over."""

    OWN_OPTIONS: ClassVar[tuple[str, ...]] = (*OpenAICompatibleProvider.OWN_OPTIONS, RELEASE_OPTION)

    def __init__(self, settings: ProviderSettings) -> None:
        super().__init__(settings)
        self.api_base_url = self._resolve_api_base_url()
        self._loaded_here: set[str] = set()

    def _resolve_api_base_url(self) -> str:
        """Where the server's own model API lives, derived from the chat endpoint or declared.

        The two roots sit side by side on one server, so deriving costs the operator nothing in the
        normal case. The override exists because a derivation is a guess about someone else's URL
        layout, and a guess must never be the only way through.
        """
        declared = self.settings.options.get(API_BASE_URL_OPTION)
        if isinstance(declared, str) and declared:
            return declared.rstrip("/")
        root = (self.settings.base_url or "").rstrip("/")
        if root.endswith(OPENAI_ROOT_SUFFIX):
            root = root[: -len(OPENAI_ROOT_SUFFIX)]
        return f"{root}/{NATIVE_API_PATH}"

    @property
    def loaded_by_this_adapter(self) -> frozenset[str]:
        """The instances this adapter loaded, as far as it knows. Never treated as the truth."""
        return frozenset(self._loaded_here)

    def _load_timeout(self) -> float:
        value = self.settings.options.get(LOAD_TIMEOUT_OPTION)
        if isinstance(value, bool) or not isinstance(value, int | float):
            return DEFAULT_LOAD_TIMEOUT_SECONDS
        return float(value)

    def _load_config(self) -> dict[str, Any]:
        """What a load performed here asks for beyond the model itself, forwarded unread.

        Unread by the same rule that already keeps the options of the chat call opaque: these are the
        product's settings and they change on its release cycle, not on this adapter's. A member the
        server does not know is refused by the server and arrives as a classified failure, which is a
        better report than a setting silently dropped on the way.

        It applies to a load this adapter performs and to nothing else. A model the server already
        holds is used as it stands, whatever it was loaded with, because reloading it would evict
        what someone else is working with - the ownership rule the whole release policy is built on.
        """
        declared = self.settings.options.get(LOAD_CONFIG_OPTION)
        return dict(declared) if isinstance(declared, dict) else {}

    def _may_release_foreign(self) -> bool:
        """Whether a run may unload a model it did not load. An operator's decision, not a flow's.

        It lives in the provider block rather than in the node because it is a fact about the
        machine and who else is using it: a workflow definition travels between installations, and
        one that could evict another person's resident model would carry that habit with it.
        """
        return bool(self.settings.options.get(RELEASE_FOREIGN_OPTION, False))

    def _native_call(self, path: str, payload: dict[str, Any] | None, timeout: float) -> tuple[object | None, str]:
        """One request to the server's model API, returning the parsed body or an explanation.

        The explanation is text rather than an exception because both callers turn it into something
        of their own: a load failure becomes a classified reply the node routes on, while a release
        failure becomes a line on the response of the run. Neither may escape as an exception here.
        """
        url = f"{self.api_base_url}/{path}"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST" if payload is not None else "GET",
        )
        credential = self.settings.credential()
        if credential is not None:
            request.add_header("Authorization", f"Bearer {credential}")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8")), ""
        except urllib.error.HTTPError as e:
            return None, f"HTTP {e.code}: {text_of(e.read().decode('utf-8', errors='replace'))}"
        except TimeoutError:
            return None, f"no answer from {url} within {timeout:g} seconds"
        except urllib.error.URLError as e:
            return None, f"{url} could not be reached: {e.reason}"
        except OSError as e:
            return None, f"the call to {url} failed on the connection: {type(e).__name__}: {e}"
        except json.JSONDecodeError as e:
            return None, f"{url} answered with a body that is not JSON: {e}"

    def _status_of(self, explanation: str) -> int | None:
        """The HTTP status an explanation names, so a failure keeps the class its status deserves."""
        if not explanation.startswith("HTTP "):
            return None
        code = explanation[len("HTTP ") :].split(":", 1)[0]
        return int(code) if code.isdigit() else None

    def _failure_from(self, explanation: str, model: str, doing: str) -> ProviderReply:
        status = self._status_of(explanation)
        error_class = classify_status(status, explanation) if status is not None else ProviderErrorClass.TRANSIENT
        return ProviderReply.failure(error_class, f"{doing} failed: {explanation}", model=model)

    def _instances_of(self, model: str, timeout: float) -> tuple[list[str] | None, str]:
        """Which instances of one model the server currently holds, asked rather than remembered."""
        payload, explanation = self._native_call(MODELS_PATH, None, timeout)
        if payload is None:
            return None, explanation
        entries = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            return None, f"the model listing of {self.api_base_url} carries no 'models' list"
        for entry in entries:
            if isinstance(entry, dict) and entry.get("key") == model:
                loaded = entry.get("loaded_instances")
                instances = loaded if isinstance(loaded, list) else []
                return [
                    instance[LISTED_INSTANCE_ID_KEY]
                    for instance in instances
                    if isinstance(instance, dict) and isinstance(instance.get(LISTED_INSTANCE_ID_KEY), str)
                ], ""
        return [], ""

    def _loaded_instance_ids(self, timeout: float) -> tuple[set[str] | None, str]:
        """Every instance the server holds right now, across all models, or why it could not be asked."""
        payload, explanation = self._native_call(MODELS_PATH, None, timeout)
        if payload is None:
            return None, explanation
        entries = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            return None, f"the model listing of {self.api_base_url} carries no 'models' list"
        return {
            instance[LISTED_INSTANCE_ID_KEY]
            for entry in entries
            if isinstance(entry, dict) and isinstance(entry.get("loaded_instances"), list)
            for instance in entry["loaded_instances"]
            if isinstance(instance, dict) and isinstance(instance.get(LISTED_INSTANCE_ID_KEY), str)
        }, ""

    def _ensure_loaded(self, model: str, timeout: float) -> ProviderReply | None:
        """Load the model unless the server already holds it, and return a failure where it cannot.

        A model the server already holds is left alone and is deliberately *not* recorded as this
        adapter's: whoever put it there owns it, and the release rules follow that ownership.
        """
        instances, explanation = self._instances_of(model, timeout)
        if instances is None:
            return self._failure_from(explanation, model, "Reading which models the server holds")
        if instances:
            return None
        # The model is written last on purpose: a load configuration cannot redirect the load onto
        # another model, and every rule about what this adapter may release rests on that ownership.
        request = {**self._load_config(), "model": model}
        payload, explanation = self._native_call(LOAD_PATH, request, self._load_timeout())
        if payload is None:
            return self._failure_from(explanation, model, f"Loading the model '{model}'")
        instance_id = payload.get(INSTANCE_ID_KEY) if isinstance(payload, dict) else None
        if not isinstance(instance_id, str) or not instance_id:
            return ProviderReply.failure(
                ProviderErrorClass.PERMANENT,
                f"The load of model '{model}' answered without an '{INSTANCE_ID_KEY}': {text_of(payload)}",
                model=model,
            )
        self._loaded_here.add(instance_id)
        return None

    def _release_instance(self, instance_id: str, timeout: float) -> str:
        """Unload one instance, returning an explanation where it did not happen."""
        _, explanation = self._native_call(UNLOAD_PATH, {INSTANCE_ID_KEY: instance_id}, timeout)
        self._loaded_here.discard(instance_id)
        return explanation

    def _release_model(self, model: str, timeout: float) -> str:
        """Release what this adapter is allowed to release of one model, after a call asked for it.

        The server is asked what it holds rather than the memory being trusted: another process may
        have unloaded the instance already, and an instance this adapter never loaded is left where
        it is unless the operator widened the permission.
        """
        instances, explanation = self._instances_of(model, timeout)
        if instances is None:
            return explanation
        may_release_foreign = self._may_release_foreign()
        failures = [
            failure
            for instance_id in instances
            if instance_id in self._loaded_here or may_release_foreign
            if (failure := self._release_instance(instance_id, timeout))
        ]
        return "; ".join(failures)

    def complete(self, call: ProviderCall) -> ProviderReply:
        """Make sure the model is resident, perform the inherited call, then release if asked.

        The release happens whether the call was answered or refused: a node that asked for the
        memory back asked for it either way, and a failed call has just as little use for a resident
        model as a successful one.
        """
        timeout = self._timeout(call.options)
        failure = self._ensure_loaded(call.model, timeout)
        if failure is not None:
            return failure
        reply = super().complete(call)
        if call.options.get(RELEASE_OPTION):
            self._release_model(call.model, timeout)
        return reply

    def finalize(self, reason: FinalizeReason) -> None:
        """Release what this adapter loaded, unless the run only paused. See ADR 014 §2.

        The engine reports the outcome and holds no policy; this is the policy. A pause keeps the
        model, because the answer that resumes the run is expected shortly and a release there buys
        an unload and a reload for nothing. Every other reason ends the run or rebuilds the seat, and
        a model held for a run that is over is held for no one.
        """
        if reason in KEEP_LOADED_ON:
            return
        timeout = self._timeout({})
        still_loaded, explanation = self._loaded_instance_ids(timeout)
        if still_loaded is not None:
            # The server is right: an instance it no longer holds was released by someone else, and
            # asking it to release the model twice would report a failure where nothing is wrong.
            for gone in self._loaded_here - still_loaded:
                self._loaded_here.discard(gone)
        failures = [
            f"{instance_id}: {failure}"
            for instance_id in sorted(self._loaded_here)
            if (failure := self._release_instance(instance_id, timeout))
        ]
        if still_loaded is None and failures:
            # The listing could not be read, so the releases above were attempted blind; say so,
            # because otherwise the report names the unload rather than the reason it went blind.
            failures.append(f"the model listing could not be read first: {explanation}")
        if failures:
            raise LmStudioResidencyError(
                f"Provider '{self.name}' could not release {len(failures)} model(s) it loaded: {'; '.join(failures)}"
            )
