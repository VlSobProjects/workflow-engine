from prettytable import PrettyTable

from workflow_engine.output import ActionNodeOutput


def dict_list_to_pretty_table(dict_list: list[dict[str, object]]) -> ActionNodeOutput:
    if not dict_list:
        return ActionNodeOutput(output_text="", error_code="pretty_table_no_data")
    table = PrettyTable()
    table.field_names = list(dict_list[0].keys())
    for item in dict_list:
        table.add_row(list(item.values()))
    return ActionNodeOutput(output_text=str(table))
