"""Text rendering of help DTOs. No business logic: renderers only format what the DTOs carry."""

import json

from workflow_engine.help_contract.models import (
    COLLECTION_KEYS,
    ActionComponent,
    ComponentType,
    HelpComponent,
    HelpParameter,
    get_component_type_description,
)

_INDENT = "    "


def _wrap(text: str, indent: str) -> list[str]:
    return [f"{indent}{line.strip()}" for line in text.strip().splitlines() if line.strip()]


def _parameter_lines(parameters: dict[str, HelpParameter]) -> list[str]:
    lines = ["Parameters:"]
    for name, parameter in parameters.items():
        requiredness = "required" if parameter.required else "optional"
        lines.append(f"{_INDENT}{name} ({parameter.type}, {requiredness}): {parameter.description}")
    return lines


class TextComponentRenderer:
    """Renders one help component for the operator terminal."""

    def __init__(self, component: HelpComponent):
        self.component = component

    def render(self) -> str:
        component = self.component
        lines = [
            f"Name: {component.name}",
            f"Type: {component.component_type.value}",
            f"Source: {component.source.value}",
            f"Summary: {component.summary}",
            "Description:",
            *_wrap(component.description, _INDENT),
        ]
        if component.parameters:
            lines.extend(_parameter_lines(component.parameters))
        if isinstance(component, ActionComponent):
            lines.extend(self._action_lines(component))
        if component.notes:
            lines.append("Notes:")
            lines.extend(f"{_INDENT}- {note}" for note in component.notes)
        lines.append("About this component type:")
        lines.extend(_wrap(get_component_type_description(component.component_type), _INDENT))
        return "\n".join(lines)

    @staticmethod
    def _action_lines(component: ActionComponent) -> list[str]:
        lines = [f"Execution mode: {component.execution_mode}"]
        if component.node_template:
            lines.append("Node template:")
            lines.extend(f"{_INDENT}{line}" for line in json.dumps(component.node_template, indent=2).splitlines())
        if component.transition_hints:
            lines.append("Transition hints:")
            lines.extend(f"{_INDENT}- {hint}" for hint in component.transition_hints)
        for example in component.examples:
            lines.append(f"Example: {example['title']}")
            lines.extend(f"{_INDENT}{line}" for line in json.dumps(example["node"], indent=2).splitlines())
        return lines


def render_components_list_text(components: dict[ComponentType, list[HelpComponent]]) -> str:
    """Renders the per-type component list for the operator terminal."""
    lines: list[str] = []
    for component_type, items in components.items():
        lines.append(f"{COLLECTION_KEYS[component_type]}:")
        for component in items:
            marker = "" if component.source.value == "core" else f" [{component.source.value}]"
            lines.append(f"{_INDENT}{component.name}{marker}: {component.summary}")
    return "\n".join(lines)
