from string import Template

from workflow_engine.actions.action_present import PresentResponse


class SimplePresentResponseRender:
    def __init__(self, present_response: PresentResponse):
        self.present_response = present_response

    def render(self) -> str:
        template = Template(
            "====================== PresentResponse ======================\n"
            "Title: $title\n"
            "Description:\n"
            "$description\n"
            "Instruction:\n"
            "$instruction\n"
            "Hints:\n"
            "$hints\n"
            "Errors:\n"
            "$errors\n"
            "=============================================================\n"
        )
        return template.substitute(
            title=self.present_response.title,
            description=self.present_response.description,
            instruction=self.present_response.instruction,
            hints="\n".join([f"- {hint}" for hint in self.present_response.hints])
            if self.present_response.hints
            else "",
            errors="\n".join(f"{k}: {v}" for k, v in self.present_response.errors.items())
            if self.present_response.errors
            else "",
        )
