import json

from graphs.llm import llm
from graphs.models import TableData
from graphs.prompts import edit_table_prompt
from graphs.states import EditTableState

edit_table_llm = llm.with_structured_output(TableData)
edit_table_chain = edit_table_prompt | edit_table_llm

MAX_EDIT_HISTORY = 4

def _format_previous_edits(history: list[dict]) -> str:
    if not history:
        return "None"
    parts = []
    for i, op in enumerate(history[-MAX_EDIT_HISTORY:], start=1):
        parts.append(
            f"Edit {i}:\n"
            f"- instructions: {op['instructions']}\n"
            f"- original table: {json.dumps(op['original_table'], ensure_ascii=False)}\n"
            f"- edited table: {json.dumps(op['edited_table'], ensure_ascii=False)}"
        )
    return "\n\n".join(parts)


def edit_tables_node(state: EditTableState) -> EditTableState:
    print("[edit-tables] instructions:", state["instructions"])
    print("[edit-tables] current table:", json.dumps(state["table"], ensure_ascii=False))

    previous_edits = _format_previous_edits(state.get("edit_history", []))

    result: TableData = edit_table_chain.invoke({
        "native_language": state["native_language"],
        "target_language": state["target_language"],
        "instructions": state["instructions"],
        "previous_edits": previous_edits,
        "table_json": json.dumps(state["table"], ensure_ascii=False, indent=2),
    })

    edited_table = result.model_dump()
    print("[edit-tables] edited table:", json.dumps(edited_table, ensure_ascii=False))

    edit_op = {
        "instructions": state["instructions"],
        "original_table": state["table"],
        "edited_table": edited_table,
    }
    new_history = [*state.get("edit_history", []), edit_op]

    return {
        **state,
        "edited_table": edited_table,
        "edit_history": new_history,
    }
