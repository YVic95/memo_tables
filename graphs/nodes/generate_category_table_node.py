from graphs.llm import llm
from graphs.models import TableData
from graphs.prompts import generate_table_prompt, generate_verb_table_prompt
from graphs.states import GenerateTableState

CATEGORY_PROMPTS = {
    "verb": generate_verb_table_prompt,
    # "noun": generate_noun_table_prompt,
    # "pronoun": generate_pronoun_table_prompt,
    # "adjective": generate_adjective_table_prompt,
    # "adverb": generate_adverb_table_prompt,
}

def generate_category_table_node(state: GenerateTableState) -> GenerateTableState:
    slug = state.get("word_category_slug")
    prompt = CATEGORY_PROMPTS.get(slug, generate_table_prompt)

    chain = prompt | llm.with_structured_output(TableData)

    result: TableData = chain.invoke({
        "native_language": state["native_language"],
        "target_language": state["target_language"],
        "rule_name": state["rule_name"],
        "rule_description": state["rule_description"] or "",
    })

    return {
        **state,
        "general_table": result.model_dump(),
    }
