from workflow_engine.help_contract.guard_catalog import GuardCatalogEntry
from workflow_engine.help_contract.models import ComponentSource, GuardComponent


def adapt_guard(entry: GuardCatalogEntry) -> GuardComponent:
    """Adapt a guard catalog entry into its help component. Guard kinds are always core."""
    return GuardComponent(
        name=entry.name,
        source=ComponentSource.CORE,
        summary=entry.summary,
        description=entry.description,
        parameters=dict(entry.parameters) or None,
        notes=entry.notes or None,
        kind=entry.kind,
    )
