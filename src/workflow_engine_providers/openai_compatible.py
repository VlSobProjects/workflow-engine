"""The `openai_compatible` adapter: one chat completion over plain HTTP. See ADR 014 §2.

The protocol is the one every local model server and every hosted vendor now speaks - a POST of a
message list to ``<base_url>/chat/completions`` - so a single adapter reaches a model running on
the operator's own machine and a model behind a paid endpoint without knowing which is which. It is
written on the standard library alone: a vendor SDK would buy nothing here beyond a dependency, and
the engine's rule is that the standard library comes first.

What the adapter does not do is as deliberate as what it does. It keeps no conversation, because a
node holds no dialogue; it manages no model residency, because this protocol has no such operation;
and it never raises a transport failure, because a failure is a value the node routes on.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any, ClassVar

from workflow_engine.exceptions import WorkflowConfigurationError
from workflow_engine.providers.base_provider import (
    BaseProvider,
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

ADAPTER_NAME = "openai_compatible"

CHAT_COMPLETIONS_PATH = "chat/completions"
DEFAULT_TIMEOUT_SECONDS = 120.0
ERROR_BODY_LIMIT = 500

TIMEOUT_OPTION = "timeout"
SYSTEM_OPTION = "system"
ADAPTER_OWN_OPTIONS = (TIMEOUT_OPTION, SYSTEM_OPTION)
"""The two keys this adapter consumes itself; every other option is sent to the server unread."""

_CONTEXT_OVERFLOW_MARKERS = (
    "context length",
    "context_length",
    "context size",
    "context_size",
    "context window",
    "maximum context",
    "too many tokens",
    "prompt is too long",
    "reduce the length",
)
"""Substrings by which a refusal of an oversized prompt is told apart from any other bad request.

There is no status code for it and no cross-vendor error code, so the body is the only signal. A
marker that is missed costs the run a routable overflow, not a wrong answer: the call still fails,
as ``invalid_request`` or ``transient`` by its status, and the branch that would have split the data
is simply not taken.

The list grows by measurement and never by imagination. The ``size`` wordings were added in session
``2026-08-25-implementation-2``, when a local server first refused an oversized prompt on demand -
``exceeds the available context size``, under an error type of the same word - and every marker
written before it missed the one refusal the class exists for. The same wording later arrived under a
500 from an Ollama decision endpoint, which is why the markers are read in the 5xx range too.
"""


def _as_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def text_of(payload: object, limit: int = ERROR_BODY_LIMIT) -> str:
    text = payload if isinstance(payload, str) else str(payload)
    return text if len(text) <= limit else text[:limit] + "..."


def classify_status(status: int, body: str) -> ProviderErrorClass:
    """Map one HTTP status onto the fixed classes of ADR 014 §5.

    Public inside this package: an adapter that adds endpoints of its own classifies their failures
    by the same rule, so one server never reports two different classes for the same status.

    The split that matters is the refusal of an oversized prompt: it is the one honest overflow signal
    the engine can get - it carries no tokenizer - and a guard that sees the class routes the run into
    a branch that splits the data. The body is read for it in the 4xx and the 5xx range alike, because
    servers differ in the status they give it: an Ollama decision endpoint refuses with a 500 and
    ``Context size has been exceeded.``, and classing that by its status alone would retry a call that
    can only fail the same way.
    """
    if status == 429:
        return ProviderErrorClass.RATE_LIMITED
    if status == 408:
        return ProviderErrorClass.TIMEOUT
    if status == 413:
        return ProviderErrorClass.CONTEXT_OVERFLOW
    if status in (401, 403):
        # A credential the server rejects is not fixed by calling again, and the run must not spend
        # its attempts finding that out.
        return ProviderErrorClass.PERMANENT
    if status >= 400 and _names_an_overflow(body):
        return ProviderErrorClass.CONTEXT_OVERFLOW
    if status >= 500:
        return ProviderErrorClass.TRANSIENT
    if status >= 400:
        return ProviderErrorClass.INVALID_REQUEST
    return ProviderErrorClass.TRANSIENT


def _names_an_overflow(body: str) -> bool:
    lowered = body.lower()
    return any(marker in lowered for marker in _CONTEXT_OVERFLOW_MARKERS)


@register_provider(
    description="Calls a chat completion endpoint speaking the OpenAI-compatible HTTP protocol.",
    provider_type=ADAPTER_NAME,
    notes=[
        "Reaches a model server running on the operator's own machine and a hosted vendor alike: "
        "what differs between them is the 'base_url' and whether a credential is needed.",
        "'base_url' is required and is the root the endpoint hangs off, without the "
        f"'/{CHAT_COMPLETIONS_PATH}' suffix - typically the '/v1' root of the server.",
        "The credential is read from the environment variable named by 'api_key_env' at the moment "
        "of the call, and is sent as a bearer token. A server that needs none declares none.",
        f"Every call option except '{TIMEOUT_OPTION}' and '{SYSTEM_OPTION}' is sent to the server as "
        "a field of the request body, so temperature, token limits and any server-specific field "
        "reach it without this adapter knowing them.",
    ],
    metadata=ProviderOperatorMetadata(
        description=(
            "Sends the prompt as a single user message to '<base_url>/chat/completions' and returns "
            "the content of the first choice, together with the model the server reports and the "
            "token counts it reports. Every transport failure comes back as one of the six error "
            "classes rather than as an exception: 429 is 'rate_limited', a timeout is 'timeout', a "
            "refusal of an oversized prompt is 'context_overflow', a rejected credential is "
            "'permanent', another 4xx is 'invalid_request', and another 5xx or an unreachable server "
            "is 'transient'."
        ),
        call_options={
            SYSTEM_OPTION: ProviderOptionDoc(
                type="string",
                description=(
                    "A system message placed before the prompt. Declare it in the provider block's "
                    "'options' to apply it to every call, or on the node to apply it to one."
                ),
            ),
            TIMEOUT_OPTION: ProviderOptionDoc(
                type="number",
                description=(
                    "Seconds to wait for the reply before the call fails as 'timeout'. Defaults to "
                    f"the provider block's '{TIMEOUT_OPTION}' option, then to {DEFAULT_TIMEOUT_SECONDS:g}."
                ),
            ),
        },
        configuration_keys=("adapter", "base_url", "model", "api_key_env", "options"),
    ),
)
class OpenAICompatibleProvider(BaseProvider):
    """An adapter over the OpenAI-compatible chat completion endpoint of any server.

    It holds nothing between calls - the protocol offers no residency operation - so it does not
    override ``finalize``: an adapter with nothing to release has nothing to say when a run ends.
    """

    OWN_OPTIONS: ClassVar[tuple[str, ...]] = ADAPTER_OWN_OPTIONS
    """The options this adapter consumes rather than sends on. A subclass that understands more of
    them extends this, so an instruction meant for the adapter never reaches the server as a field
    of the request."""

    def __init__(self, settings: ProviderSettings) -> None:
        super().__init__(settings)
        if not settings.base_url:
            raise WorkflowConfigurationError(
                f"Provider '{settings.name}' uses the '{ADAPTER_NAME}' adapter and must declare "
                f"'base_url': the address of the server, without the '/{CHAT_COMPLETIONS_PATH}' suffix."
            )
        self.endpoint = f"{settings.base_url.rstrip('/')}/{CHAT_COMPLETIONS_PATH}"

    def _option(self, options: Mapping[str, object], key: str) -> object | None:
        """One option as the call asks for it, else as the provider block asks for it. See ADR 014 §3.

        The node wins over the configuration by the same rule the ``model`` field follows: the block
        states how this installation reaches the provider, the node states what this one step needs.
        """
        if key in options:
            return options[key]
        return self.settings.options.get(key)

    def _timeout(self, options: Mapping[str, object]) -> float:
        value = self._option(options, TIMEOUT_OPTION)
        if isinstance(value, bool) or not isinstance(value, int | float):
            return DEFAULT_TIMEOUT_SECONDS
        return float(value)

    def _messages(self, call: ProviderCall) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        system = self._option(call.options, SYSTEM_OPTION)
        if isinstance(system, str) and system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": call.prompt})
        return messages

    def _request(self, call: ProviderCall) -> urllib.request.Request:
        body: dict[str, Any] = {"model": call.model, "messages": self._messages(call)}
        body.update({key: value for key, value in call.options.items() if key not in self.OWN_OPTIONS})
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        credential = self.settings.credential()
        if credential is not None:
            headers["Authorization"] = f"Bearer {credential}"
        return urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )

    def _reply_from(self, payload: object, model: str) -> ProviderReply:
        """Read the answer out of a chat completion response, or refuse the response as permanent.

        A body that is not a chat completion means the configured address is not the endpoint this
        adapter speaks to. Calling again cannot make it one, so it is ``permanent`` rather than
        ``transient``: the operator has to change the configuration, and a retry loop would only
        delay them learning that.
        """
        if not isinstance(payload, dict):
            return ProviderReply.failure(
                ProviderErrorClass.PERMANENT,
                f"The endpoint {self.endpoint} answered with {type(payload).__name__}, not a chat completion object.",
                model=model,
            )
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            return ProviderReply.failure(
                ProviderErrorClass.PERMANENT,
                f"The endpoint {self.endpoint} answered without a usable 'choices' list: {text_of(payload)}",
                model=model,
            )
        message = choices[0].get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            return ProviderReply.failure(
                ProviderErrorClass.PERMANENT,
                f"The endpoint {self.endpoint} answered with a choice carrying no text content: {text_of(payload)}",
                model=model,
            )
        reported = payload.get("model")
        return ProviderReply.answer(
            content,
            model=reported if isinstance(reported, str) and reported else model,
            usage=self._usage_from(payload.get("usage")),
        )

    def _usage_from(self, usage: object) -> ProviderUsage | None:
        """The token counts the server reported, and nothing where it reported none. See ADR 014 §4."""
        if not isinstance(usage, dict):
            return None
        prompt_tokens = _as_int(usage.get("prompt_tokens"))
        completion_tokens = _as_int(usage.get("completion_tokens"))
        if prompt_tokens is None and completion_tokens is None:
            return None
        return ProviderUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)

    def complete(self, call: ProviderCall) -> ProviderReply:
        """Perform one chat completion, returning its reply or its classified failure.

        Nothing leaves this method as an exception. The node that made the call routes on an error
        class, so a server that is down, a credential that is refused and a prompt that does not fit
        are all values here - each one a different branch of the graph, none of them a crash.
        """
        model = call.model
        try:
            with urllib.request.urlopen(self._request(call), timeout=self._timeout(call.options)) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = text_of(e.read().decode("utf-8", errors="replace"))
            return ProviderReply.failure(
                classify_status(e.code, body),
                f"The endpoint {self.endpoint} refused the call with HTTP {e.code}: {body}",
                model=model,
            )
        except TimeoutError:
            return ProviderReply.failure(
                ProviderErrorClass.TIMEOUT,
                f"The endpoint {self.endpoint} did not answer within {self._timeout(call.options):g} seconds.",
                model=model,
            )
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError):
                return ProviderReply.failure(
                    ProviderErrorClass.TIMEOUT,
                    f"The endpoint {self.endpoint} did not answer within {self._timeout(call.options):g} seconds.",
                    model=model,
                )
            return ProviderReply.failure(
                ProviderErrorClass.TRANSIENT,
                f"The endpoint {self.endpoint} could not be reached: {e.reason}",
                model=model,
            )
        except OSError as e:
            return ProviderReply.failure(
                ProviderErrorClass.TRANSIENT,
                f"The call to {self.endpoint} failed on the connection: {type(e).__name__}: {e}",
                model=model,
            )
        except json.JSONDecodeError as e:
            return ProviderReply.failure(
                ProviderErrorClass.PERMANENT,
                f"The endpoint {self.endpoint} answered with a body that is not JSON: {e}",
                model=model,
            )
        return self._reply_from(payload, model)
