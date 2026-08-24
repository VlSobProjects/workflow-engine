"""The seat of provider instances: one adapter object per configured provider name. See ADR 014 §2-3.

The seat is module state, like the registries themselves, and for the same reason: a component that
is not the engine has to reach it. A registered function shipped by an adapter package - the
sanctioned way to tell a local server to release its model - receives only the state view and the
previous output, so a seat owned by the engine object would be unreachable from the very place that
needs it. The cost is that one process has one seat: two engines in it share their providers, which
for one model server is the truth rather than a compromise, and tests reset it between runs.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from workflow_engine.exceptions import WorkflowConfigurationError
from workflow_engine.providers.base_provider import BaseProvider, FinalizeReason, ProviderSettings
from workflow_engine.registry.provider_registry import get_registered_provider

_SETTINGS: dict[str, ProviderSettings] = {}
_SEATED: dict[str, BaseProvider] = {}


def install_provider_settings(settings: Mapping[str, ProviderSettings]) -> None:
    """Install the configured providers, releasing any seated instance whose settings changed.

    Called once per bootstrap. Reinstalling the same configuration keeps the instances: a process
    that builds an engine twice must not lose what an adapter remembers about the model server.
    """
    for name, seated in list(_SEATED.items()):
        if settings.get(name) != _SETTINGS.get(name):
            _release(name, seated, FinalizeReason.RECONFIGURED)
    _SETTINGS.clear()
    _SETTINGS.update(settings)


def configured_providers() -> MappingProxyType[str, ProviderSettings]:
    """The installed provider configuration, as the engine resolves it. See ADR 014 §3."""
    return MappingProxyType(_SETTINGS)


def resolve_provider(name: str) -> BaseProvider:
    """The adapter instance answering for a configured provider name, seated on first use.

    Both failures are configuration errors and neither is routable: a node naming a provider the
    installation does not configure, and a configured block naming an adapter no loaded module
    registered, are wrong before the run rather than during it.
    """
    seated = _SEATED.get(name)
    if seated is not None:
        return seated
    settings = _SETTINGS.get(name)
    if settings is None:
        known = ", ".join(sorted(_SETTINGS)) or "none"
        raise WorkflowConfigurationError(
            f"Provider '{name}' is not configured. Configured providers: {known}. "
            f"Providers are declared in the 'providers' section of the engine configuration file."
        )
    provider = get_registered_provider(settings.adapter)(settings)
    _SEATED[name] = provider
    return provider


def seated_providers() -> tuple[str, ...]:
    """The provider names currently holding an instance in this process."""
    return tuple(_SEATED)


def finalize_providers(reason: FinalizeReason) -> dict[str, str]:
    """Finalize and unseat every instance, reporting the adapters that failed to release.

    A failure to release is reported, never raised: the run has already reached its outcome, and a
    model left resident must not turn a completed workflow into a failed one. The instance is
    dropped either way, because an adapter that failed to release holds no state worth trusting.
    """
    failures: dict[str, str] = {}
    for name, seated in list(_SEATED.items()):
        failure = _release(name, seated, reason)
        if failure is not None:
            failures[name] = failure
    return failures


def reset_providers() -> None:
    """Drop the seat and the installed configuration, releasing the instances first."""
    finalize_providers(FinalizeReason.RECONFIGURED)
    _SETTINGS.clear()


def _release(name: str, provider: BaseProvider, reason: FinalizeReason) -> str | None:
    del _SEATED[name]
    try:
        provider.finalize(reason)
    except Exception as e:  # noqa: BLE001 - an adapter's failure to release is reported, not raised
        return f"{type(e).__name__}: {e}"
    return None
