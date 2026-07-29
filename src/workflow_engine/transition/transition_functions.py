from workflow_engine.engine import add_dynamic_workflow_node
from workflow_engine.models.state import StateModel
from workflow_engine.registry.function_registry import register_transaction


# @register_transaction
# def stop_on_error_transaction(output: str,state: StateModel, errors: list[str] | None) -> str | None:
#     """A transaction function that stops the workflow on error."""
#     from workflow_engine.workflow import stop_on_error_node_factory
#
#     if errors is None or state.error_code is not None and state.error_code in errors:
#         return add_dynamic_workflow_node(stop_on_error_node_factory(output))
#     return None
