
class StateError(Exception):
    """Exception raised for errors in state."""
    def __init__(self, message: str) -> None:
        super().__init__(message)


class WorkflowError(Exception):
    """Exception raised for errors in workflow."""
    def __init__(self, message: str) -> None:
        super().__init__(message)

class ActionError(Exception):
    """Exception raised for errors in action."""

class ActionRegistryError(ActionError):
    """Exception raised for errors in action registry."""


class ActionConfigError(ActionError):
    """Exception raised for errors in action config."""

class RuntimeParameterError(Exception):
    """Exception raised for errors in runtime parameters."""
    def __init__(self, param_name: str, current_node_id: str, param_value: str | None, message: str | None) -> None:
        self.param_name = param_name
        self.current_node_id = current_node_id
        self.param_value = param_value
        self.message = message
        super().__init__(f"Runtime parameter error: {param_name}={param_value}, {message}")