"""Canonical DTOs of the operator help contract. See ADR 009.

The payload shapes produced here are a stable contract: key names and structural
nesting must not change; extension is allowed only through new optional fields.
"""

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import ClassVar, Final

CONTRACT_VERSION: Final[str] = "1.0"

MISSING_METADATA_TEXT: Final[str] = "Description is not provided by the external component."


class ComponentSource(Enum):
    CORE = "core"
    EXTERNAL = "external"


class ComponentType(Enum):
    ACTION = "action"
    FUNCTION = "function"
    VALIDATOR = "validator"
    GUARD = "guard"
    CODEC = "codec"
    PROVIDER = "provider"


COLLECTION_KEYS: Final[MappingProxyType[ComponentType, str]] = MappingProxyType(
    {
        ComponentType.ACTION: "actions",
        ComponentType.FUNCTION: "functions",
        ComponentType.VALIDATOR: "validators",
        ComponentType.GUARD: "guards",
        ComponentType.CODEC: "codecs",
        ComponentType.PROVIDER: "providers",
    }
)

COMPONENT_TYPE_BY_KEY: Final[MappingProxyType[str, ComponentType]] = MappingProxyType(
    {key: c_type for c_type, key in COLLECTION_KEYS.items()}
)

COMPONENT_TYPE_DESCRIPTION: Final[MappingProxyType[ComponentType, str]] = MappingProxyType(
    {
        ComponentType.ACTION: (
            "An action performs the work of one workflow node. A node selects it by 'action_type' "
            "and configures it through 'action_parameters'. An automatic action runs and the engine "
            "continues; an interactive action returns instructions and waits for operator input."
        ),
        ComponentType.FUNCTION: (
            "A registered function executed by a function-running action. A node selects it by "
            "'function_name' and passes 'function_parameters'. Parameter values support "
            "'param.<name>' and 'output.<node_id>' references resolved from the workflow state. "
            "Beside them the engine injects two arguments no node configures, for a function that "
            "declares them: 'state', the read-only state view, and 'output', the ActionNodeOutput "
            "the node received - the previous node's output, or the accepted answer at an "
            "interactive node."
        ),
        ComponentType.VALIDATOR: (
            "A registered function returning a boolean, used by the 'function_name' guard and by "
            "the 'validators' post-condition shorthand of a node."
        ),
        ComponentType.GUARD: (
            "A guard is the predicate of a transition. It is declared inside a transition under the "
            "'guard' or 'validator' key, and the first transition whose guard holds is taken. "
            "The name of a guard is the error code of a node that fails it."
        ),
        ComponentType.CODEC: (
            "A codec persists a typed value in the workflow state, so a parameter keeps its Python "
            "type across a save and a load. Codecs are selected by value type automatically; "
            "workflow definitions do not reference them directly."
        ),
        ComponentType.PROVIDER: (
            "A provider adapter performs the model call of an 'llm' node. A node selects a provider "
            "by the name the 'providers' section of the engine configuration gives it, and that "
            "section says which adapter answers for the name, at which base URL, with which default "
            "model and under which environment variable the credential is read. Call options travel "
            "to the adapter unread by the engine, so the options listed here are the ones this "
            "adapter acts on."
        ),
    }
)


def get_component_type_description(component_type: ComponentType) -> str:
    return COMPONENT_TYPE_DESCRIPTION[component_type]


@dataclass(frozen=True)
class HelpParameter:
    """Documentation of one configuration parameter: display type, description, requiredness, kind.

    ``template`` marks the parameter template text, the kind ADR 016 defines: references resolve
    inside its value instead of only as the whole of it.
    """

    type: str
    description: str
    required: bool = True
    template: bool = False

    def to_payload(self) -> dict[str, object]:
        return {
            "type": self.type,
            "description": self.description,
            "required": self.required,
            "template": self.template,
        }


@dataclass(frozen=True)
class HelpComponent:
    name: str
    source: ComponentSource
    summary: str
    description: str
    parameters: dict[str, HelpParameter] | None
    notes: tuple[str, ...] | None
    component_type: ClassVar[ComponentType]

    def to_payload(self) -> dict[str, object]:
        """The stable detail payload: name, type, summary, description, parameters, source, notes."""
        parameters: dict[str, object] | None = None
        if self.parameters is not None:
            parameters = {name: parameter.to_payload() for name, parameter in self.parameters.items()}
        return {
            "name": self.name,
            "type": self.component_type.value,
            "summary": self.summary,
            "description": self.description,
            "parameters": parameters,
            "source": self.source.value,
            "notes": list(self.notes) if self.notes else None,
        }

    def to_list_payload(self) -> dict[str, object]:
        """The stable list payload: one line per component."""
        return {"name": self.name, "summary": self.summary, "source": self.source.value}


@dataclass(frozen=True)
class ActionComponent(HelpComponent):
    component_type: ClassVar[ComponentType] = ComponentType.ACTION
    execution_mode: str
    node_template: dict[str, object]
    action_parameters: dict[str, list[str]]
    transition_hints: tuple[str, ...]
    examples: tuple[dict[str, object], ...]

    def to_payload(self) -> dict[str, object]:
        payload = super().to_payload()
        payload.update(
            {
                "execution_mode": self.execution_mode,
                "node_template": self.node_template,
                "action_parameters": self.action_parameters,
                "transition_hints": list(self.transition_hints),
                "examples": list(self.examples),
            }
        )
        return payload


@dataclass(frozen=True)
class FunctionComponent(HelpComponent):
    component_type: ClassVar[ComponentType] = ComponentType.FUNCTION


@dataclass(frozen=True)
class ValidatorComponent(HelpComponent):
    component_type: ClassVar[ComponentType] = ComponentType.VALIDATOR


@dataclass(frozen=True)
class GuardComponent(HelpComponent):
    component_type: ClassVar[ComponentType] = ComponentType.GUARD
    kind: str = "guard"

    def to_payload(self) -> dict[str, object]:
        payload = super().to_payload()
        payload["kind"] = self.kind
        return payload


@dataclass(frozen=True)
class ProviderComponent(HelpComponent):
    component_type: ClassVar[ComponentType] = ComponentType.PROVIDER
    configuration_keys: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        payload = super().to_payload()
        payload["configuration_keys"] = list(self.configuration_keys)
        return payload


@dataclass(frozen=True)
class CodecComponent(HelpComponent):
    component_type: ClassVar[ComponentType] = ComponentType.CODEC
    python_type: str = ""

    def to_payload(self) -> dict[str, object]:
        payload = super().to_payload()
        payload["python_type"] = self.python_type
        return payload
