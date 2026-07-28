from collections.abc import Callable

VALIDATION_OUTPUT_ERROR = "validation_output_error"

ERROR_CODES:dict[str, str] = {
    VALIDATION_OUTPUT_ERROR: "Error encountered during output validation"
}



def error_registration(fun: Callable[[],dict[str, str]]) -> Callable[[],dict[str, str]]:
    """Decorator to register error codes and messages."""
    error_dict = fun()
    ERROR_CODES.update(error_dict)
    return fun