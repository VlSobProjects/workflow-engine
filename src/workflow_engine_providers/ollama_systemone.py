"""The `ollama_systemone` adapter: typed questions to a decision model, probabilities back. See ADR 014 §2.

A decision model writes no text. It is given a state and named questions - yes or no (`noul`), one of
several options (`choice`), a level on a scale (`score`) - and answers each with a probability, over
Ollama's own endpoint ``POST /v1/systemone``. The contract of ADR 014 carries that without a change:
the prompt is the state, the questions travel in the call options the engine never reads, and the
reply is a JSON object of question name to answer, which an `llm` node with ``format: json`` binds
through its codecs like any other reply. A `noul` answer is the probability of yes as a number; a
`choice` or `score` answer is the object the server returned for it, without its type, so nothing
the server said is lost on the way to the bus.

It is a sibling of `openai_compatible` rather than a subclass: the endpoint, the request and the
reply are all different, and only the rule that turns a status into an error class is shared.

Ollama loads a model on the first call that names it and keeps it for a keep-alive period, so the
adapter performs no load. What it does keep is the ownership rule `lmstudio` keeps: a model the run
brought onto the server is released when the run ends, unless the run only paused, and a model the
server was already holding is left where it is.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar

from workflow_engine.exceptions import WorkflowConfigurationError, WorkflowRuntimeError
from workflow_engine.providers.base_provider import (
    BaseProvider,
    FinalizeReason,
    ProviderCall,
    ProviderErrorClass,
    ProviderReply,
    ProviderSettings,
    ProviderUsage,
)
from workflow_engine.registry.provider_registry import (
    ProviderOperatorMetadata,
    ProviderOptionDoc,
    register_provider,
)
from workflow_engine_providers.openai_compatible import classify_status, text_of

ADAPTER_NAME = "ollama_systemone"

SYSTEMONE_PATH = "systemone"
OPENAI_ROOT_SUFFIX = "/v1"
NATIVE_API_PATH = "api"
# Relative to the native API root, which already carries NATIVE_API_PATH.
RUNNING_PATH = "ps"
GENERATE_PATH = "generate"

DEFAULT_TIMEOUT_SECONDS = 120.0
DEFAULT_TAG = "latest"

QUESTIONS_OPTION = "questions"
TIMEOUT_OPTION = "timeout"
KEEP_ALIVE_OPTION = "keep_alive"
API_BASE_URL_OPTION = "api_base_url"
ADAPTER_OWN_OPTIONS = (QUESTIONS_OPTION, TIMEOUT_OPTION, KEEP_ALIVE_OPTION)
"""The keys this adapter reads itself; every other call option is sent to the server unread.

``questions`` and ``keep_alive`` reach the server too, but only after the adapter has resolved them:
the questions are required, and the keep-alive may come from the provider block as well as the node.
"""

NOUL_TYPE = "noul"
KEEP_LOADED_ON = (FinalizeReason.PAUSED,)
"""The one outcome that keeps a model resident: an answer is expected shortly. See ADR 014 §2."""


def _as_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _model_key(model: str) -> str:
    """One spelling for a model name, so a name without a tag matches what the server lists.

    The server resolves ``laya`` to ``laya:latest`` and lists the latter; comparing the two as given
    would call the run's own model foreign and leave it resident.
    """
    return model if ":" in model.rsplit("/", 1)[-1] else f"{model}:{DEFAULT_TAG}"


@dataclass(frozen=True, slots=True)
class _Exchange:
    """One request to the server: the parsed body, or why there is none and what class that is."""

    payload: object | None = None
    error_class: ProviderErrorClass | None = None
    explanation: str = ""


@dataclass(slots=True)
class _ServerResidency:
    """Which models the run brought onto one server, and which provider block brought each.

    Per server and not per block, for the reason `lmstudio` counts it so: two blocks pointing at one
    machine share its memory, and a model one block brought is not foreign to the other.
    """

    brought: dict[str, str] = field(default_factory=dict)


_RESIDENCY: dict[str, _ServerResidency] = {}
"""Per native API root, what this run brought there. Module state, as the provider seat is."""


def reset_residency() -> None:
    """Forget what the run brought, releasing nothing: the server keeps whatever it keeps."""
    _RESIDENCY.clear()


class OllamaResidencyError(WorkflowRuntimeError):
    """A model the run brought onto the server could not be released when the run ended.

    Raised out of ``finalize``, which is how the seat reports a failure to release on the response of
    the run without changing its outcome or its exit code. See ADR 014 §2.
    """


@register_provider(
    description="Asks a decision model on an Ollama server typed questions and returns their probabilities.",
    provider_type=ADAPTER_NAME,
    notes=[
        "'base_url' is required and is the '/v1' root of the server; the call goes to "
        f"'<base_url>/{SYSTEMONE_PATH}'. A local server needs no credential; one declared by "
        "'api_key_env' is sent as a bearer token.",
        "The resolved prompt is the state the questions are about. The questions are the call option "
        f"'{QUESTIONS_OPTION}', an object of question name to question in the server's own form, sent "
        "unread: what a question may say is the server's vocabulary, and a question it refuses comes "
        "back as 'invalid_request'.",
        "The reply is a JSON object of question name to answer: the probability of yes for a 'noul' "
        "question, and for a 'choice' or 'score' question the object the server returned without its "
        "type. Bind it with 'format: json', a 'float' for a 'noul' answer and a 'dict' for the others.",
        "A model the server did not hold before the call is the run's own and is released when the run "
        "ends, unless the run only paused. A model the server already held is never released.",
        "The model's context is the one its model file sets: the server ignores a context option on a "
        "decision call, and the adapter performs no load that could set one. A larger context is a model "
        "variant whose model file raises 'num_ctx' and 'num_batch' together, named as 'model'. The input of "
        "one call is bounded by the smaller of the two, so the 'context_length' the server reports overstates "
        "the bound when 'num_batch' is smaller; an input above it comes back as 'context_overflow'.",
    ],
    metadata=ProviderOperatorMetadata(
        description=(
            f"Sends the prompt as the state and the '{QUESTIONS_OPTION}' option as the questions to "
            f"'<base_url>/{SYSTEMONE_PATH}', and returns the answers as a JSON object of question name "
            "to answer, together with the token counts the server reports. Every transport failure "
            "comes back as one of the six error classes rather than as an exception: a refused request "
            "is 'invalid_request', an input too large for the server is 'context_overflow', a timeout "
            "is 'timeout', another 5xx or an unreachable server is 'transient', and a body that is not a "
            "System One answer is 'permanent'."
        ),
        call_options={
            QUESTIONS_OPTION: ProviderOptionDoc(
                type="object",
                description=(
                    "Required. Question name to question: 'type' ('noul', 'choice' or 'score'), "
                    "'instructions' and, as the type needs, 'criteria'. Several questions about one "
                    "state are asked in one call."
                ),
            ),
            KEEP_ALIVE_OPTION: ProviderOptionDoc(
                type="string or number",
                description=(
                    "How long the server keeps the model after the call, as the server reads it: a "
                    "duration such as '5m', or seconds; 0 releases it right after the call. Declared "
                    "on the node or in the provider block's 'options'; the server's own setting applies "
                    "when neither declares it."
                ),
            ),
            TIMEOUT_OPTION: ProviderOptionDoc(
                type="number",
                description=(
                    "Seconds to wait for the answer, which includes loading the model on the first "
                    f"call, before the call fails as 'timeout'. Defaults to the provider block's "
                    f"'{TIMEOUT_OPTION}' option, then to {DEFAULT_TIMEOUT_SECONDS:g}."
                ),
            ),
        },
        configuration_keys=("adapter", "base_url", "model", "api_key_env", "options", API_BASE_URL_OPTION),
    ),
)
class OllamaSystemOneProvider(BaseProvider):
    """An adapter over the System One endpoint that releases the models the run brought."""

    OWN_OPTIONS: ClassVar[tuple[str, ...]] = ADAPTER_OWN_OPTIONS

    def __init__(self, settings: ProviderSettings) -> None:
        super().__init__(settings)
        if not settings.base_url:
            raise WorkflowConfigurationError(
                f"Provider '{settings.name}' uses the '{ADAPTER_NAME}' adapter and must declare "
                f"'base_url': the '/v1' root of the server, without the '/{SYSTEMONE_PATH}' suffix."
            )
        self.endpoint = f"{settings.base_url.rstrip('/')}/{SYSTEMONE_PATH}"
        self.api_base_url = self._resolve_api_base_url()

    def _resolve_api_base_url(self) -> str:
        """Where the server's own API lives, derived from the '/v1' root or declared."""
        declared = self.settings.options.get(API_BASE_URL_OPTION)
        if isinstance(declared, str) and declared:
            return declared.rstrip("/")
        root = (self.settings.base_url or "").rstrip("/")
        if root.endswith(OPENAI_ROOT_SUFFIX):
            root = root[: -len(OPENAI_ROOT_SUFFIX)]
        return f"{root}/{NATIVE_API_PATH}"

    def _option(self, options: Mapping[str, object], key: str) -> object | None:
        """One option as the call asks for it, else as the provider block asks for it. See ADR 014 §3."""
        if key in options:
            return options[key]
        return self.settings.options.get(key)

    def _timeout(self, options: Mapping[str, object]) -> float:
        value = self._option(options, TIMEOUT_OPTION)
        if isinstance(value, bool) or not isinstance(value, int | float):
            return DEFAULT_TIMEOUT_SECONDS
        return float(value)

    def _residency(self) -> _ServerResidency:
        return _RESIDENCY.setdefault(self.api_base_url, _ServerResidency())

    @property
    def brought_by_this_adapter(self) -> frozenset[str]:
        """The models this block brought onto the server, as far as the run knows."""
        return frozenset(model for model, owner in self._residency().brought.items() if owner == self.name)

    def _exchange(self, url: str, payload: dict[str, Any] | None, timeout: float) -> _Exchange:
        """One request, returning the parsed body or a classified explanation. Never raises."""
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
                return _Exchange(payload=json.loads(response.read().decode("utf-8")))
        except urllib.error.HTTPError as e:
            body = text_of(e.read().decode("utf-8", errors="replace"))
            return _Exchange(error_class=classify_status(e.code, body), explanation=f"HTTP {e.code}: {body}")
        except TimeoutError:
            return _Exchange(
                error_class=ProviderErrorClass.TIMEOUT, explanation=f"no answer within {timeout:g} seconds"
            )
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError):
                return _Exchange(
                    error_class=ProviderErrorClass.TIMEOUT, explanation=f"no answer within {timeout:g} seconds"
                )
            return _Exchange(error_class=ProviderErrorClass.TRANSIENT, explanation=f"could not be reached: {e.reason}")
        except OSError as e:
            return _Exchange(
                error_class=ProviderErrorClass.TRANSIENT,
                explanation=f"failed on the connection: {type(e).__name__}: {e}",
            )
        except json.JSONDecodeError as e:
            return _Exchange(
                error_class=ProviderErrorClass.PERMANENT, explanation=f"answered with a body that is not JSON: {e}"
            )

    def _resident_models(self, timeout: float) -> set[str] | None:
        """The models the server holds right now, or None when it could not be asked."""
        exchange = self._exchange(f"{self.api_base_url}/{RUNNING_PATH}", None, timeout)
        entries = exchange.payload.get("models") if isinstance(exchange.payload, dict) else None
        if not isinstance(entries, list):
            return None
        return {
            _model_key(name)
            for entry in entries
            if isinstance(entry, dict)
            for name in (entry.get("name"), entry.get("model"))
            if isinstance(name, str) and name
        }

    def _note_ownership(self, model: str, timeout: float) -> None:
        """Record the model as the run's when the server does not hold it before the call.

        A listing that cannot be read records nothing, which is the safe side of the rule: a model
        the run cannot prove it brought is never released by it. The call itself goes ahead, since
        the server loads the model whether or not the adapter knows who owns it.
        """
        key = _model_key(model)
        residency = self._residency()
        if key in residency.brought:
            return
        resident = self._resident_models(timeout)
        if resident is not None and key not in resident:
            residency.brought[key] = self.name

    def _request_body(self, call: ProviderCall, questions: object) -> dict[str, Any]:
        body: dict[str, Any] = {key: value for key, value in call.options.items() if key not in self.OWN_OPTIONS}
        body.update({"model": call.model, "state": call.prompt, QUESTIONS_OPTION: questions})
        keep_alive = self._option(call.options, KEEP_ALIVE_OPTION)
        if keep_alive is not None:
            body[KEEP_ALIVE_OPTION] = keep_alive
        return body

    def _reply_from(self, payload: object, model: str) -> ProviderReply:
        """Flatten the answers to question name to answer, or refuse the body as permanent.

        A body without an ``answers`` object means the configured address is not this endpoint, which
        calling again cannot fix. See ``openai_compatible`` for the same rule over chat completions.
        """
        answers = payload.get("answers") if isinstance(payload, dict) else None
        if not isinstance(answers, dict):
            return ProviderReply.failure(
                ProviderErrorClass.PERMANENT,
                f"The endpoint {self.endpoint} answered without an 'answers' object: {text_of(payload)}",
                model=model,
            )
        flat: dict[str, object] = {}
        for name, answer in answers.items():
            if not isinstance(answer, dict):
                return ProviderReply.failure(
                    ProviderErrorClass.PERMANENT,
                    f"The endpoint {self.endpoint} answered '{name}' with {type(answer).__name__}, not an object.",
                    model=model,
                )
            if answer.get("type") == NOUL_TYPE:
                flat[name] = answer.get(NOUL_TYPE)
            else:
                flat[name] = {key: value for key, value in answer.items() if key != "type"}
        reported = payload.get("model")
        return ProviderReply.answer(
            json.dumps(flat),
            model=reported if isinstance(reported, str) and reported else model,
            usage=self._usage_from(payload.get("usage")),
        )

    def _usage_from(self, usage: object) -> ProviderUsage | None:
        """The server's input and output tokens under the contract's prompt and completion names."""
        if not isinstance(usage, dict):
            return None
        prompt_tokens = _as_int(usage.get("input_tokens"))
        completion_tokens = _as_int(usage.get("output_tokens"))
        if prompt_tokens is None and completion_tokens is None:
            return None
        return ProviderUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)

    def complete(self, call: ProviderCall) -> ProviderReply:
        """Ask the questions about the prompt, returning the answers or a classified failure."""
        model = call.model
        questions = call.options.get(QUESTIONS_OPTION)
        if not isinstance(questions, dict) or not questions:
            return ProviderReply.failure(
                ProviderErrorClass.INVALID_REQUEST,
                f"The '{ADAPTER_NAME}' adapter needs the call option '{QUESTIONS_OPTION}': an object of "
                "question name to question, with at least one question.",
                model=model,
            )
        timeout = self._timeout(call.options)
        self._note_ownership(model, timeout)
        exchange = self._exchange(self.endpoint, self._request_body(call, questions), timeout)
        if exchange.error_class is not None:
            return ProviderReply.failure(
                exchange.error_class,
                f"The endpoint {self.endpoint} failed the call: {exchange.explanation}",
                model=model,
            )
        return self._reply_from(exchange.payload, model)

    def _release(self, model: str, timeout: float) -> str:
        """Ask the server to release one model, returning an explanation where it did not happen."""
        exchange = self._exchange(
            f"{self.api_base_url}/{GENERATE_PATH}", {"model": model, KEEP_ALIVE_OPTION: 0}, timeout
        )
        self._residency().brought.pop(model, None)
        return exchange.explanation if exchange.error_class is not None else ""

    def finalize(self, reason: FinalizeReason) -> None:
        """Release what this block brought onto the server, unless the run only paused. See ADR 014 §2.

        The server is asked first what it still holds: a model its keep-alive already released needs
        no request, and asking for it again would report a failure where nothing is wrong.
        """
        if reason in KEEP_LOADED_ON:
            return
        timeout = self._timeout({})
        residency = self._residency()
        mine = sorted(self.brought_by_this_adapter)
        resident = self._resident_models(timeout)
        if resident is not None:
            for gone in [model for model in mine if model not in resident]:
                residency.brought.pop(gone, None)
            mine = [model for model in mine if model in resident]
        failures = [f"{model}: {failure}" for model in mine if (failure := self._release(model, timeout))]
        if resident is None and failures:
            failures.append("the list of running models could not be read first")
        if not residency.brought:
            _RESIDENCY.pop(self.api_base_url, None)
        if failures:
            raise OllamaResidencyError(
                f"Provider '{self.name}' could not release {len(failures)} model(s) the run brought: "
                f"{'; '.join(failures)}"
            )
