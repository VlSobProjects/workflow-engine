from workflow_engine.help_contract.models import (
    MISSING_METADATA_TEXT,
    CodecComponent,
    ComponentSource,
)
from workflow_engine.registry.type_registry import Codec, get_codec_metadata


def adapt_codec(codec: type[Codec], source: ComponentSource) -> CodecComponent:
    """Adapt a registered codec into its help component: explicit metadata plus the type mapping."""
    metadata = get_codec_metadata(codec.type_name())
    if metadata is not None:
        summary = metadata.summary
        description = metadata.description
    else:
        summary = MISSING_METADATA_TEXT if source is ComponentSource.EXTERNAL else ""
        description = MISSING_METADATA_TEXT if source is ComponentSource.EXTERNAL else ""
    return CodecComponent(
        name=codec.type_name(),
        source=source,
        summary=summary,
        description=description,
        parameters=None,
        notes=None,
        python_type=codec.python_type().__name__,
    )
