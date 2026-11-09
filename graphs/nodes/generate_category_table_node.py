from graphs.llm import llm
from graphs.models import AdjectiveTableLayout, TableData
from graphs.prompts import (
    generate_adjective_gender_table_prompt,
    generate_adjective_number_table_prompt,
    generate_table_prompt,
    generate_noun_table_prompt,
    generate_verb_table_prompt,
)
from graphs.states import GenerateTableState
from graphs.table_utils import (
    ADJECTIVE_COLUMN_COUNT,
    ADJECTIVE_SIDE_COLUMNS,
    NOUN_COLUMN_COUNT,
    extract_italic_markers,
    require_adjective_layout,
    require_noun_layout,
)

CATEGORY_PROMPTS = {
    "verb": generate_verb_table_prompt,
    "noun": generate_noun_table_prompt,
    # "pronoun": generate_pronoun_table_prompt,
    # "adverb": generate_adverb_table_prompt,
}


def _validate_noun_table(table: TableData) -> None:
    require_noun_layout(table.noun_table_layout)
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


def _validate_adjective_table(table: TableData) -> None:
    """Validate one unified-flow table: the adj_number_gender layout, 8x8."""
    require_adjective_layout(table.adjective_table_layout)
    if table.adjective_table_layout != AdjectiveTableLayout.adj_number_gender:
        raise ValueError(
            "Unified adjective tables must set adjective_table_layout to "
            f'"{AdjectiveTableLayout.adj_number_gender.value}", got '
            f'"{table.adjective_table_layout}"'
        )
    if len(table.headers) != ADJECTIVE_COLUMN_COUNT:
        raise ValueError(
            f"Adjective table must have {ADJECTIVE_COLUMN_COUNT} columns, "
            f"got {len(table.headers)}"
        )
    for row in table.rows:
        if len(row.cells) != ADJECTIVE_COLUMN_COUNT:
            raise ValueError(
                f"Every adjective table row must have {ADJECTIVE_COLUMN_COUNT} "
                f"cells, got {len(row.cells)}"
            )


def _adjectives_used(number_table: TableData) -> list[str]:
    """Italic-marked adjectives in the number table's form cells, in order."""
    markers: list[str] = []
    for row in number_table.rows:
        for columns in ADJECTIVE_SIDE_COLUMNS:
            form_index = columns["form"]
            if form_index < len(row.cells):
                markers.extend(extract_italic_markers(row.cells[form_index]))
    seen: set[str] = set()
    unique: list[str] = []
    for marker in markers:
        key = marker.lower()
        if key not in seen:
            seen.add(key)
            unique.append(marker)
    return unique


def _invoke_table_prompt(prompt, state: GenerateTableState, extra: dict) -> TableData:
    chain = prompt | llm.with_structured_output(TableData)
    return chain.invoke({
        "native_language": state["native_language"],
        "target_language": state["target_language"],
        "rule_name": state["rule_name"],
        "rule_description": state["rule_description"] or "",
        **extra,
    })


def _generate_adjective_tables(state: GenerateTableState) -> tuple[TableData, TableData]:
    """Run the unified flow: number table first, then gender with fresh items."""
    number_table = _invoke_table_prompt(
        generate_adjective_number_table_prompt, state, {}
    )
    _validate_adjective_table(number_table)

    avoid = ", ".join(_adjectives_used(number_table))
    gender_table = _invoke_table_prompt(
        generate_adjective_gender_table_prompt, state, {"avoid_adjectives": avoid}
    )
    _validate_adjective_table(gender_table)
    return number_table, gender_table


def generate_category_table_node(state: GenerateTableState) -> GenerateTableState:
    slug = state.get("word_category_slug")

    if slug == "adjective":
        number_table, gender_table = _generate_adjective_tables(state)
        return {
            **state,
            "general_table": number_table.model_dump(),
            "general_tables": [
                number_table.model_dump(),
                gender_table.model_dump(),
            ],
        }

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
