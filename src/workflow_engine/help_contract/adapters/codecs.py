from workflow_engine.help_contract.models import ComponentSource, CodecComponent
from workflow_engine.registry.type_registry import Codec


def adapt_codec(codec: type[Codec], source: ComponentSource) -> CodecComponent:
    return CodecComponent(
        name=codec.type_name(),
        source=source,
        summary=f"Converts {codec.type_name()}",
        description=f"Converts {codec.type_name()} to and from dictionary representation.",
        parameters=None,
        notes=None,
    )

