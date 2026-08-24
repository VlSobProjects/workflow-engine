"""The provider adapter contract: one call, one reply, one finalization. See ADR 014 §2 and §5.

The core fixes three things and nothing else: what crosses the call, which failure classes a
reply may carry, and when an adapter is told the run is over. Everything a provider does behind
that — the protocol it speaks, which model it keeps resident, how it authenticates — is the
adapter's own business, so a vendor's semantics never enter the engine's release cadence.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import ClassVar

from workflow_engine.exceptions import WorkflowConfigurationError

ADAPTER_KEY = "adapter"
BASE_URL_KEY = "base_url"
MODEL_KEY = "model"
API_KEY_ENV_KEY = "api_key_env"
OPTIONS_KEY = "options"
PROVIDER_KEYS = (ADAPTER_KEY, BASE_URL_KEY, MODEL_KEY, API_KEY_ENV_KEY, OPTIONS_KEY)


class ProviderErrorClass(Enum):
    """The fixed failure classes an adapter reports, surfaced by the node as its error code.

    ``CONTEXT_OVERFLOW`` is deliberately not a case of ``INVALID_REQUEST``: the engine carries no
    tokenizer, so the provider's refusal is the only honest overflow signal, and a guard that sees
    the class can route the run into a branch that splits the data. See ADR 014 §5.
    """

    TRANSIENT = "transient"
    RATE_LIMITED = "rate_limited"
    PERMANENT = "permanent"
    INVALID_REQUEST = "invalid_request"
    TIMEOUT = "timeout"
    CONTEXT_OVERFLOW = "context_overflow"


class FinalizeReason(Enum):
    """Why the engine is finalizing the seated providers, so the adapter can decide what to release.

    The engine reports the fact and holds no policy: a local adapter may unload a resident model on
    ``COMPLETED`` and keep it on ``PAUSED``, where the answer to a question is expected shortly,
    while an adapter that holds nothing ignores all of them.

    Four of the five are outcomes of a run. ``RECONFIGURED`` is not: it says the seat itself is
    being rebuilt - the configuration changed under it, or the process is disposing of it - so an
    adapter that reads the reason is never told a run ended when none did.
    """

    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    ABORTED = "aborted"
    RECONFIGURED = "reconfigured"


@dataclass(frozen=True, slots=True)
class ProviderUsage:
    """What a call cost, as far as the adapter is told by the provider. See ADR 014 §4."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {"prompt_tokens": self.prompt_tokens, "completion_tokens": self.completion_tokens}


@dataclass(frozen=True, slots=True)
class ProviderCall:
    """One model call as it crosses the adapter contract.

    ``options`` is opaque to the engine on purpose: temperature, token limits and anything else a
    provider understands travel through it unread, so a node stays universal and an adapter that
    does not know an option ignores it. See ADR 014 §1.
    """

    prompt: str
    model: str
    options: MappingProxyType[str, object] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True, slots=True)
class ProviderReply:
    """What an adapter returns: the reply text, or a failure carrying one of the fixed classes.

    A failure is a value, not an exception, because the node that made the call routes on it like
    on any other node error. See ADR 001 and ADR 014 §5.
    """

    text: str | None = None
    model: str | None = None
    usage: ProviderUsage | None = None
    error_class: ProviderErrorClass | None = None
    message: str | None = None

    @classmethod
    def answer(cls, text: str, model: str | None = None, usage: ProviderUsage | None = None) -> ProviderReply:
        return cls(text=text, model=model, usage=usage)

    @classmethod
    def failure(
        cls, error_class: ProviderErrorClass, message: str, model: str | None = None, usage: ProviderUsage | None = None
    ) -> ProviderReply:
        return cls(model=model, usage=usage, error_class=error_class, message=message)

    @property
    def failed(self) -> bool:
        return self.error_class is not None


def _optional_text(name: str, data: Mapping[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise WorkflowConfigurationError(f"Provider '{name}': '{key}' must be a string.")
    return value


@dataclass(frozen=True, slots=True)
class ProviderSettings:
    """The configured seat of one provider name: which adapter answers for it and how. See ADR 014 §3.

    The credential is present as the *name* of an environment variable and is read at call time, so
    no secret is held in the configuration, in this object or in its repr. ``options`` carries what
    only the named adapter understands - a request timeout, a keep-alive - by the same rule that
    keeps call options opaque.
    """

    name: str
    adapter: str
    base_url: str | None = None
    model: str | None = None
    api_key_env: str | None = None
    options: MappingProxyType[str, object] = field(default_factory=lambda: MappingProxyType({}))

    def credential(self) -> str | None:
        """The credential as the environment holds it now, or None when unset or not declared."""
        if self.api_key_env is None:
            return None
        return os.environ.get(self.api_key_env) or None

    @classmethod
    def from_dict(cls, name: str, data: Mapping[str, object]) -> ProviderSettings:
        """Read one block of the ``providers`` section, refusing anything it does not define.

        An unknown key is refused rather than ignored: adapter-specific settings have their own
        place under ``options``, so a key beside the five is a typo, and a silently ignored typo in
        a provider block is found at the first model call instead of at load.
        """
        unknown = sorted(key for key in data if key not in PROVIDER_KEYS)
        if unknown:
            raise WorkflowConfigurationError(
                f"Provider '{name}' declares unknown keys: {', '.join(unknown)}. "
                f"Known keys: {', '.join(PROVIDER_KEYS)}; adapter-specific settings go under '{OPTIONS_KEY}'."
            )
        adapter = data.get(ADAPTER_KEY)
        if not isinstance(adapter, str) or not adapter:
            raise WorkflowConfigurationError(f"Provider '{name}' must declare '{ADAPTER_KEY}' as a non-empty string.")
        options = data.get(OPTIONS_KEY, {})
        if not isinstance(options, dict):
            raise WorkflowConfigurationError(f"Provider '{name}': '{OPTIONS_KEY}' must be an object.")
        return cls(
            name=name,
            adapter=adapter,
            base_url=_optional_text(name, data, BASE_URL_KEY),
            model=_optional_text(name, data, MODEL_KEY),
            api_key_env=_optional_text(name, data, API_KEY_ENV_KEY),
            options=MappingProxyType(dict(options)),
        )

    def to_dict(self) -> dict[str, object]:
        """The block as the configuration file holds it - the credential by name, never by value."""
        return {
            ADAPTER_KEY: self.adapter,
            BASE_URL_KEY: self.base_url,
            MODEL_KEY: self.model,
            API_KEY_ENV_KEY: self.api_key_env,
            OPTIONS_KEY: dict(self.options),
        }


class BaseProvider(ABC):
    """A registered provider adapter, seated once per configured provider name in a process.

    An adapter is a class rather than a plain callable because it is allowed to remember what a
    provider is holding for it - which model a local server currently has resident - and to decide
    from that whether the next call needs a load, a swap or nothing. That memory is a cache of a
    fact that lives outside the process: a fresh process knows nothing, so an adapter must work
    when its state is empty and must never treat it as the truth.
    """

    PROVIDER_TYPE: ClassVar[str]

    def __init__(self, settings: ProviderSettings) -> None:
        self.settings = settings

    @property
    def name(self) -> str:
        """The configured provider name this instance answers for, not the adapter's own name."""
        return self.settings.name

    def resolve_model(self, model: str | None) -> str | None:
        """The model of a call: what the node asked for, or the configured default. See ADR 014 §1."""
        return model or self.settings.model

    @abstractmethod
    def complete(self, call: ProviderCall) -> ProviderReply:
        """Perform one call and return its reply or its classified failure."""

    def finalize(self, reason: FinalizeReason) -> None:
        """Release what this adapter holds, after a run reached the given outcome.

        The default does nothing: an adapter that holds nothing needs no code, and one that does
        overrides this. It is called for every outcome of every run, so it must not fail a run.
        """
        return None
