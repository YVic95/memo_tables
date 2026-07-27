from graphs.llm import llm
from graphs.models import TableData
from graphs.prompts import generate_table_prompt
from graphs.states import GenerateTableState
from crud.rules import get_grammar_rule_by_id

table_llm = llm.with_structured_output(TableData)
generate_table_chain = generate_table_prompt | table_llm

def generate_general_table_node(state: GenerateTableState) -> GenerateTableState:
    rule = get_grammar_rule_by_id(state["db"], state["grammar_rule_id"])
    if rule is None:
        raise ValueError(f"Grammar rule {state['grammar_rule_id']} not found")

    result: TableData = generate_table_chain.invoke({
        "native_language": state["native_language"],
        "target_language": state["target_language"],
        "rule_name": rule.name,
        "rule_description": rule.description or "",
    })

    return {
        **state,
        "rule_name": rule.name,
        "rule_description": rule.description,
        "general_table": result.model_dump(),
    }
