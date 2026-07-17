from graphs.llm import llm
from graphs.models import CategoryChoice
from graphs.prompts import attach_grammar_category_to_rule_prompt
from graphs.states import InitialRuleState
from crud.rules import get_word_categories

categorizer_llm = llm.with_structured_output(CategoryChoice)

def attach_grammatical_category_to_rule_node(state: InitialRuleState) -> InitialRuleState:
    rows = get_word_categories(state["db"])

    categories = "\n".join(
        f"- {row.id}: {row.name} ({row.slug})"
        for row in rows
    )

    chain = attach_grammar_category_to_rule_prompt | categorizer_llm

    result = chain.invoke({
        "rule_title": state["rule_title"],
        "rule_explanation": state["rule_explanation"],
        "categories": categories,
    })

    return {
        **state,
        "word_category_id": result.word_category_id,
    }