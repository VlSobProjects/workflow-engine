from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).parent


@pytest.fixture
def tests_dir() -> Path:
    return TESTS_DIR


@pytest.fixture
def provider_seat_guard():
    """Keep the process-wide provider registry and seat clean around a test that touches them.

    Both are module state by design (ADR 014 §2), so a test that registers an adapter or seats an
    instance would otherwise leave it for every test that runs after it.
    """
    from workflow_engine.providers.provider_seat import reset_providers
    from workflow_engine.registry import provider_registry

    registries = (
        provider_registry.PROVIDER_REGISTRY,
        provider_registry.PROVIDER_DESCRIPTIONS,
        provider_registry.PROVIDER_NOTES,
        provider_registry.PROVIDER_OPERATOR_METADATA,
    )
    snapshots = [dict(registry) for registry in registries]
    reset_providers()
    yield
    reset_providers()
    for registry, snapshot in zip(registries, snapshots, strict=True):
        registry.clear()
        registry.update(snapshot)
