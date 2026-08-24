"""The provider adapter registry, the fifth registration kind. See ADR 014 §2.

Adapters get their own registry rather than a convention over functions: the help contract owes
them their own component type, the base class checks the contract at registration, and the
``providers`` configuration section resolves adapter names in a namespace of its own.
"""

from dataclasses import dataclass, field
from typing import TypeVar

from workflow_engine.exceptions import WorkflowConfigurationError
from workflow_engine.providers.base_provider import BaseProvider

T = TypeVar("T", bound=BaseProvider)


@dataclass(frozen=True)
class ProviderOptionDoc:
    """Operator documentation of one call option an adapter understands."""

    type: str
    description: str


@dataclass(frozen=True)
class ProviderOperatorMetadata:
    """What an operator needs to configure and call this adapter, shown by help. See ADR 009.

    ``call_options`` is where an opaque option becomes discoverable: the engine passes the mapping
    of a node through unread, so the adapter's own help entry is the only place that can state
    which keys it acts on. ``configuration_keys`` names the fields of its ``providers`` block.
    """

    description: str
    call_options: dict[str, ProviderOptionDoc] = field(default_factory=dict)
    configuration_keys: tuple[str, ...] = ()


PROVIDER_REGISTRY: dict[str, type[BaseProvider]] = {}
PROVIDER_DESCRIPTIONS: dict[str, str] = {}
PROVIDER_NOTES: dict[str, list[str] | None] = {}
PROVIDER_OPERATOR_METADATA: dict[str, ProviderOperatorMetadata | None] = {}


def register_provider(
    description: str,
    provider_type: str | None = None,
    notes: list[str] | None = None,
    metadata: ProviderOperatorMetadata | None = None,
):
    def decorator(cls: type[T]) -> type[T]:
        if not issubclass(cls, BaseProvider):
            raise WorkflowConfigurationError(
                f"Provider '{cls.__name__}' does not implement the provider contract: it is not a BaseProvider."
            )
        key = provider_type or getattr(cls, "PROVIDER_TYPE", None)
        if not key:
            raise WorkflowConfigurationError(
                f"Provider '{cls.__name__}' declares no name: set PROVIDER_TYPE or pass provider_type."
            )

        if key in PROVIDER_REGISTRY:
            raise WorkflowConfigurationError(
                f"Provider adapter '{key}' is already registered for class '{PROVIDER_REGISTRY[key].__name__}'. "
                f"Cannot register class '{cls.__name__}' for the same adapter name."
            )

        cls.PROVIDER_TYPE = key
        PROVIDER_REGISTRY[key] = cls
        PROVIDER_DESCRIPTIONS[key] = description
        PROVIDER_NOTES[key] = notes
        PROVIDER_OPERATOR_METADATA[key] = metadata
        return cls

    return decorator


def get_registered_provider(adapter: str) -> type[BaseProvider]:
    cls = PROVIDER_REGISTRY.get(adapter)
    if cls is None:
        known = ", ".join(sorted(PROVIDER_REGISTRY)) or "none"
        raise WorkflowConfigurationError(
            f"Provider adapter '{adapter}' is not registered. Registered adapters: {known}"
        )
    return cls


def get_registered_providers_info() -> dict[str, str]:
    return PROVIDER_DESCRIPTIONS


def get_summary_for_provider(adapter: str) -> str:
    get_registered_provider(adapter)
    return PROVIDER_DESCRIPTIONS[adapter]


def get_notes_for_provider(adapter: str) -> list[str] | None:
    get_registered_provider(adapter)
    return PROVIDER_NOTES[adapter]


def get_metadata_for_provider(adapter: str) -> ProviderOperatorMetadata | None:
    get_registered_provider(adapter)
    return PROVIDER_OPERATOR_METADATA[adapter]
