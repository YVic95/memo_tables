from graphs.llm import llm
from graphs.models import TableData
from graphs.prompts import (
    generate_table_prompt,
    generate_noun_table_prompt,
    generate_verb_table_prompt,
)
from graphs.states import GenerateTableState

NOUN_LAYOUTS = frozenset({"noun_number", "noun_gender"})
NOUN_COLUMN_COUNT = 8

CATEGORY_PROMPTS = {
    "verb": generate_verb_table_prompt,
    "noun": generate_noun_table_prompt,
    # "pronoun": generate_pronoun_table_prompt,
    # "adjective": generate_adjective_table_prompt,
    # "adverb": generate_adverb_table_prompt,
}


def _validate_noun_table(table: TableData) -> None:
    if table.noun_table_layout not in NOUN_LAYOUTS:
        raise ValueError(
            "Noun table must set noun_table_layout to 'noun_number' or 'noun_gender'"
        )
    if len(table.headers) != NOUN_COLUMN_COUNT:
        raise ValueError(
            f"Noun table must have {NOUN_COLUMN_COUNT} columns, got {len(table.headers)}"
        )
    for row in table.rows:
        if len(row.cells) != NOUN_COLUMN_COUNT:
            raise ValueError(
                f"Every noun table row must have {NOUN_COLUMN_COUNT} cells, "
                f"got {len(row.cells)}"
            )


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

    if slug == "noun":
        _validate_noun_table(result)

    return {
        **state,
        "general_table": result.model_dump(),
    }
