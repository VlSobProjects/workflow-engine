class WorkflowEngineError(Exception):
    """Exception raised for errors in workflow."""
    def __init__(self, message: str) -> None:
        super().__init__(message)

class WorkflowConfigurationError(WorkflowEngineError):
    """Exception raised for errors in configuration."""

class WorkflowRuntimeError(WorkflowEngineError):
    """Exception raised for errors in runtime."""

class ActionConfigurationError(WorkflowConfigurationError):
    """Exception raised for errors in action configuration."""
    def __init__(self, action_name: str, message: str | None = None) -> None:
        self.action_name = action_name
        self.message = message
        super().__init__(f"Action configuration error in '{action_name}': {message}")

class ActionRuntimeError(WorkflowRuntimeError):
    """Exception raised for errors in runtime."""
    def __init__(self, action_name: str, message: str | None = None) -> None:
        self.action_name = action_name
        self.message = message
        super().__init__(f"Action runtime error in '{action_name}': {message}")

class WorkflowParameterConfigurationError(WorkflowConfigurationError):
    """Exception raised for errors in workflow parameter configuration."""

class WorkflowParameterError(WorkflowEngineError):
    """Exception raised for errors in parameter configuration."""
    def __init__(self, param_name: str,param_type:type,expected_type:type, message: str | None = None) -> None:
        self.param_name = param_name
        self.param_type = param_type
        self.expected_type = expected_type
        self.message = message
        super().__init__(
            f"Parameter configuration error in '{param_name}' "
            f"of type: '{param_type.__name__}' "
            f"expected type: '{expected_type.__name__}'"
            f"{f' message: {message}' if message is not None else ''}"
        )

class FunctionConfigurationError(WorkflowConfigurationError):
    """Exception raised for errors in function configuration."""

    def __init__(
        self, function_name: str, parameters: dict[str, object] | None = None, message: str | None = None
    ) -> None:
        self.function_name = function_name
        self.parameters = parameters
        self.message = message
        super().__init__(
            f"Function configuration error in '{function_name}' "
            f"with parameters '{parameters}': {message if message is not None else 'No message'}"
        )

class FunctionRuntimeError(WorkflowRuntimeError):
    """Exception raised for errors in runtime."""
    def __init__(
            self, function_name: str, parameters:dict[str, object] | None = None, message: str | None = None
    ) -> None:
        self.function_name = function_name
        self.parameters = parameters
        self.message = message
        super().__init__(
            f"Function runtime error in '{function_name}' "
            f"with parameters '{parameters}': {message if message is not None else 'No message'}"
        )

class TransitionConfigurationError(WorkflowConfigurationError):
    """Exception raised for errors in transition configuration."""
    def __init__(self, name:str, parameters:dict[str,object], message: str | None = None) -> None:
        self.name = name
        self.parameters = parameters
        self.message = message
        super().__init__(
            f"Transition configuration error in '{name}' "
            f"with parameters '{parameters}': {message if message is not None else 'No message'}"
        )

class StateLoadError(WorkflowRuntimeError):
    def __init__(self, parameter_name: str, message: str | None = None) -> None:
        self.parameter_name = parameter_name
        self.message = message
        super().__init__(
            f"State load parameter '{parameter_name}' error : "
            f"{message if message is not None else 'No message'}"
        )

class StateLoadParameterError(WorkflowRuntimeError):
    def __init__(self,current_node:str, parameter_name: str, message: str | None = None) -> None:
        self.current_node = current_node
        self.parameter_name = parameter_name
        self.message = message
        super().__init__(
            f"State load parameter error in node '{current_node}' for parameter '{parameter_name}': "
            f"{message if message is not None else 'No message'}"
        )

# class StateError(Exception):
#     """Exception raised for errors in state."""
#
#     def __init__(self, message: str) -> None:
#         super().__init__(message)
#
#
# class WorkflowError(Exception):
#     """Exception raised for errors in workflow."""
#
#     def __init__(self, message: str) -> None:
#         super().__init__(message)
#
#
# class ActionError(Exception):
#     """Exception raised for errors in action."""
#
#
# class ActionRegistryError(ActionError):
#     """Exception raised for errors in action registry."""
#
#
# class ActionConfigError(ActionError):
#     """Exception raised for errors in action config."""
#
#
# class RuntimeParameterError(Exception):
#     """Exception raised for errors in runtime parameters."""
#
#     def __init__(self, param_name: str, current_node_id: str, param_value: str | None, message: str | None) -> None:
#         self.param_name = param_name
#         self.current_node_id = current_node_id
#         self.param_value = param_value
#         self.message = message
#         super().__init__(f"Runtime parameter error: {param_name}={param_value}, {message}")
#
#
# class FunctionArgsError(Exception):
#     """Exception raised for errors in function args."""
#
#     def __init__(self, func_name: str, errors: list[str]) -> None:
#         self.errors = errors
#         self.func_name = func_name
#         super().__init__(f"Runtime Function args error in function '{func_name}': " + "; ".join(errors))
#
#
# class FunctionParametersTypeError(FunctionArgsError):
#     """Exception raised for errors in function args."""
#
#     def __init__(self, func_name: str, exception: TypeError) -> None:
#         super().__init__(func_name=func_name, errors=[exception.__str__()])
