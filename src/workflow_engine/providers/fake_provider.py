"""The `fake` adapter: the null implementation of the provider contract. See ADR 014 §6.

Not a provider. It is what makes a bare install answer for a model step at all: the action's own
tests, the shipped example workflows and the help surface of an installation with no plugin stand
on it, and no test ever reaches a network. Its replies are scripted, so a run over it is exact.
"""

from __future__ import annotations

from workflow_engine.exceptions import WorkflowConfigurationError
from workflow_engine.providers.base_provider import (
    BaseProvider,
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

REPLIES_OPTION = "replies"
REPLY_OPTION = "reply"
ERROR_OPTION = "error"
MESSAGE_OPTION = "message"
TEXT_KEY = "text"


def _error_class(value: object, source: str) -> ProviderErrorClass:
    try:
        return ProviderErrorClass(value)
    except ValueError as ex:
        known = ", ".join(item.value for item in ProviderErrorClass)
        raise WorkflowConfigurationError(
            f"The fake provider was scripted with an unknown error class '{value}' in {source}. Known classes: {known}"
        ) from ex


@register_provider(
    description="Scripted replies with no network, the null implementation of the provider contract.",
    provider_type="fake",
    notes=[
        "A call option wins over the scripted sequence, and the sequence is consumed one entry per call.",
        "With nothing scripted the reply is the prompt itself, so a test reads back what the node sent.",
    ],
    metadata=ProviderOperatorMetadata(
        description=(
            "Answers a call without leaving the process. What it answers is scripted, in this order: "
            "the 'reply' or 'error' option of the call, then the next entry of the 'replies' sequence "
            "in the provider configuration, then the prompt itself. A scripted entry is either a "
            "string, an object with 'text', or an object with 'error' and an optional 'message'."
        ),
        call_options={
            REPLY_OPTION: ProviderOptionDoc(type="string", description="The exact text this one call returns."),
            ERROR_OPTION: ProviderOptionDoc(
                type="string",
                description=(
                    "Fail this one call with the named error class: "
                    + ", ".join(item.value for item in ProviderErrorClass)
                    + "."
                ),
            ),
            MESSAGE_OPTION: ProviderOptionDoc(
                type="string", description="The message carried by a scripted failure of this call."
            ),
        },
        configuration_keys=("adapter", "model", REPLIES_OPTION),
    ),
)
class FakeProvider(BaseProvider):
    """A provider that answers from a script and remembers how far the script has been consumed."""

    def __init__(self, settings: ProviderSettings) -> None:
        super().__init__(settings)
        self.calls = 0
        self.last_finalize_reason: FinalizeReason | None = None

    def _scripted(self) -> object | None:
        replies = self.settings.options.get(REPLIES_OPTION)
        if not isinstance(replies, list) or self.calls >= len(replies):
            return None
        return replies[self.calls]

    def complete(self, call: ProviderCall) -> ProviderReply:
        model = self.resolve_model(call.model)
        try:
            if ERROR_OPTION in call.options:
                error = _error_class(call.options[ERROR_OPTION], "a call option")
                message = str(call.options.get(MESSAGE_OPTION, "scripted failure"))
                return ProviderReply.failure(error, message, model=model)
            if REPLY_OPTION in call.options:
                return ProviderReply.answer(str(call.options[REPLY_OPTION]), model=model)

            entry = self._scripted()
            if isinstance(entry, str):
                return ProviderReply.answer(entry, model=model)
            if isinstance(entry, dict):
                if ERROR_OPTION in entry:
                    error = _error_class(entry[ERROR_OPTION], "the scripted sequence")
                    message = str(entry.get(MESSAGE_OPTION, "scripted failure"))
                    return ProviderReply.failure(error, message, model=model)
                return ProviderReply.answer(str(entry.get(TEXT_KEY, "")), model=model)
            return ProviderReply.answer(call.prompt, model=model)
        finally:
            self.calls += 1

    def finalize(self, reason: FinalizeReason) -> None:
        """Hold nothing, and remember what the engine reported, so a test can read the reason back."""
        self.last_finalize_reason = reason
