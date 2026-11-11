import re

from graphs.llm import llm
from graphs.models import AdjectiveTableLayout, TableData
from graphs.prompts import (
    generate_adjective_gender_table_prompt,
    generate_adjective_number_table_prompt,
    generate_adjective_other_table_prompt,
    generate_table_prompt,
    generate_noun_table_prompt,
    generate_verb_table_prompt,
)
from graphs.states import GenerateTableState
from graphs.table_utils import (
    ADJECTIVE_COLUMN_COUNT,
    ADJECTIVE_OTHER_COLUMN_COUNT,
    ADJECTIVE_SIDE_COLUMNS,
    NOUN_COLUMN_COUNT,
    general_tables_from_table,
    require_adjective_layout,
    require_noun_layout,
)

CATEGORY_PROMPTS = {
    "verb": generate_verb_table_prompt,
    "noun": generate_noun_table_prompt,
    # "pronoun": generate_pronoun_table_prompt,
    # "adverb": generate_adverb_table_prompt,
}

_SPECIAL_TOPIC_ADJECTIVE_STEMS = (
    # Special-topic adjective rules in the Spanish canonical catalog. Catalog
    # names and descriptions are authored in English for the current pair.
    "demonstrativ",
    "possessiv",
    "comparativ",
    "superlativ",
    "apocop",
    "indefinit",
    "interrogativ",
    "ordinal",
)


def is_special_topic_adjective_rule(
    rule_name: str | None, rule_description: str | None
) -> bool:
    """Recognize special-topic rules from the Spanish adjective catalog.

    The current Spanish catalog uses English names and descriptions. General
    singular/plural, gender, and noun-adjective agreement rules fall through to
    the layout prompt; its special-topic entries always use OTHER.
    """
    source = f"{rule_name or ''} {rule_description or ''}".casefold()
    words = re.findall(r"[a-z]+", source)
    return any(
        word.startswith(stem)
        for word in words
        for stem in _SPECIAL_TOPIC_ADJECTIVE_STEMS
    )


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
    """Validate one adjective table: a known layout and 8 columns/cells."""
    require_adjective_layout(table.adjective_table_layout)
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


def _validate_adjective_other_table(table: TableData) -> None:
    """Validate an other-rules table: the adj_other layout and 4x4 shape."""
    require_adjective_layout(table.adjective_table_layout)
    if table.adjective_table_layout != AdjectiveTableLayout.adj_other:
        raise ValueError(
            "Other-rule adjective tables must set adjective_table_layout to "
            f'"{AdjectiveTableLayout.adj_other.value}", got '
            f'"{table.adjective_table_layout}"'
        )
    if len(table.headers) != ADJECTIVE_OTHER_COLUMN_COUNT:
        raise ValueError(
            f"Adjective other table must have {ADJECTIVE_OTHER_COLUMN_COUNT} "
            f"columns, got {len(table.headers)}"
        )
    for row in table.rows:
        if len(row.cells) != ADJECTIVE_OTHER_COLUMN_COUNT:
            raise ValueError(
                "Every adjective other table row must have "
                f"{ADJECTIVE_OTHER_COLUMN_COUNT} cells, got {len(row.cells)}"
            )


def _used_carrier_phrases(number_table: TableData) -> list[str]:
    """Form-cell phrases of the number table, in order, markers stripped.

    Table cells hold plain phrases ("el libro rojo"); any "*" markers from
    older generations are stripped so the gender prompt receives clean text.
    """
    phrases: list[str] = []
    for row in number_table.rows:
        for columns in ADJECTIVE_SIDE_COLUMNS:
            form_index = columns["form"]
            if form_index < len(row.cells):
                phrase = row.cells[form_index].replace("*", "").strip()
                if phrase:
                    phrases.append(phrase)
    seen: set[str] = set()
    unique: list[str] = []
    for phrase in phrases:
        key = phrase.lower()
        if key not in seen:
            seen.add(key)
            unique.append(phrase)
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


def _generate_adjective_tables(state: GenerateTableState) -> tuple[TableData, ...]:
    """Run the adjective flow from the entry table's layout choice.

    Special adjective topics in the Spanish catalog route directly to OTHER.
    Otherwise, the entry prompt returns the NUMBER table of a unified pair
    ("adj_number_gender", followed by the gender companion with fresh items),
    a single AGREEMENT table ("adj_agreement"), or a single OTHER table
    ("adj_other", never fragmented downstream).
    """
    target_language = (state.get("target_language") or "").strip().casefold()
    is_spanish_target = target_language in {"spanish", "español", "espanol"}
    if is_spanish_target and is_special_topic_adjective_rule(
        state.get("rule_name"), state.get("rule_description")
    ):
        other_table = _invoke_table_prompt(
            generate_adjective_other_table_prompt, state, {}
        )
        _validate_adjective_other_table(other_table)
        return (other_table,)

    entry_table = _invoke_table_prompt(
        generate_adjective_number_table_prompt, state, {}
    )
    require_adjective_layout(entry_table.adjective_table_layout)

    if entry_table.adjective_table_layout == AdjectiveTableLayout.adj_other:
        _validate_adjective_other_table(entry_table)
        return (entry_table,)

    _validate_adjective_table(entry_table)
    if entry_table.adjective_table_layout == AdjectiveTableLayout.adj_agreement:
        return (entry_table,)

    avoid = ", ".join(_used_carrier_phrases(entry_table))
    gender_table = _invoke_table_prompt(
        generate_adjective_gender_table_prompt, state, {"avoid_phrases": avoid}
    )
    _validate_adjective_table(gender_table)
    return (entry_table, gender_table)


def generate_category_table_node(state: GenerateTableState) -> GenerateTableState:
    slug = state.get("word_category_slug")

    if slug == "adjective":
        tables = _generate_adjective_tables(state)
        return {
            **state,
            "general_tables": [table.model_dump() for table in tables],
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
        "general_tables": general_tables_from_table(result),
    }
