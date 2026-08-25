from workflow_engine.help_contract.models import (
    MISSING_METADATA_TEXT,
    ComponentSource,
    HelpParameter,
    ProviderComponent,
)
from workflow_engine.providers.base_provider import BaseProvider
from workflow_engine.registry.provider_registry import (
    ProviderOperatorMetadata,
    get_metadata_for_provider,
    get_notes_for_provider,
    get_summary_for_provider,
)


def adapt_provider(provider: type[BaseProvider], source: ComponentSource) -> ProviderComponent:
    """Adapt a registered provider adapter into its help component.

    The parameters of a provider are its call options: the engine passes the option mapping of a
    node through without reading it, so this entry is the only place that can tell an author which
    keys the adapter acts on. They are optional by construction - an unknown option is ignored.
    """
    adapter = provider.PROVIDER_TYPE
    summary = get_summary_for_provider(adapter)
    metadata = get_metadata_for_provider(adapter)
    notes = get_notes_for_provider(adapter)
    if metadata is None:
        metadata = ProviderOperatorMetadata(
            description=MISSING_METADATA_TEXT if source is ComponentSource.EXTERNAL else ""
        )
    parameters = {
        name: HelpParameter(type=doc.type, description=doc.description, required=False)
        for name, doc in metadata.call_options.items()
    }
    return ProviderComponent(
        name=adapter,
        source=source,
        summary=summary or (MISSING_METADATA_TEXT if source is ComponentSource.EXTERNAL else ""),
        description=metadata.description,
        parameters=parameters or None,
        notes=tuple(notes) if notes else None,
        configuration_keys=tuple(metadata.configuration_keys),
    )
