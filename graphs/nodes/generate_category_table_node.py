import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from langchain_core.prompts import BasePromptTemplate

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
    require_adjective_layout,
    require_noun_layout,
)


@dataclass(frozen=True)
class LayoutPolicy:
    """Generation and validation policy for one declared table layout."""

    validator: str
    companion_prompt_role: str | None = None
    companion_context: str | None = None
    companion_validator: str | None = None


@dataclass(frozen=True)
class SpecialTopicPolicy:
    """Criteria and route for catalog topics with a dedicated table shape."""

    target_languages: frozenset[str]
    topic_stems: tuple[str, ...]
    prompt_role: str
    validator: str


@dataclass(frozen=True)
class CategoryConfig:
    """Prompt and table-generation policy for one word category."""

    prompt: BasePromptTemplate | None = None
    validator: str | None = None
    prompt_roles: Mapping[str, BasePromptTemplate] = field(default_factory=dict)
    entry_prompt_role: str | None = None
    layout_field: str | None = None
    layout_validator: str | None = None
    layout_routes: Mapping[str, LayoutPolicy] = field(default_factory=dict)
    special_topic: SpecialTopicPolicy | None = None


CATEGORY_CONFIG: dict[str, CategoryConfig] = {
    "verb": CategoryConfig(prompt=generate_verb_table_prompt),
    "noun": CategoryConfig(
        prompt=generate_noun_table_prompt,
        validator="noun",
    ),
    "adjective": CategoryConfig(
        prompt_roles={
            "entry": generate_adjective_number_table_prompt,
            "gender_companion": generate_adjective_gender_table_prompt,
            "other": generate_adjective_other_table_prompt,
        },
        entry_prompt_role="entry",
        layout_field="adjective_table_layout",
        layout_validator="adjective_layout",
        layout_routes={
            AdjectiveTableLayout.adj_number_gender.value: LayoutPolicy(
                validator="adjective_pair",
                companion_prompt_role="gender_companion",
                companion_context="avoid_carrier_phrases",
                companion_validator="adjective_pair",
            ),
            AdjectiveTableLayout.adj_agreement.value: LayoutPolicy(
                validator="adjective_pair",
            ),
            AdjectiveTableLayout.adj_other.value: LayoutPolicy(
                validator="adjective_other",
            ),
        },
        special_topic=SpecialTopicPolicy(
            target_languages=frozenset({"spanish", "español", "espanol"}),
            # Catalog titles and descriptions are authored in English for the
            # current Spanish adjective pair.
            topic_stems=(
                "demonstrativ",
                "possessiv",
                "comparativ",
                "superlativ",
                "apocop",
                "indefinit",
                "interrogativ",
                "ordinal",
            ),
            prompt_role="other",
            validator="adjective_other",
        ),
    ),
}


def _validate_noun_table(table: TableData) -> None:
    require_noun_layout(table.noun_table_layout)
    if len(table.headers) != NOUN_COLUMN_COUNT:
        raise ValueError(
            f"Noun table must have {NOUN_COLUMN_COUNT} columns, "
            f"got {len(table.headers)}"
        )
    for row in table.rows:
        if len(row.cells) != NOUN_COLUMN_COUNT:
            raise ValueError(
                f"Every noun table row must have {NOUN_COLUMN_COUNT} cells, "
                f"got {len(row.cells)}"
            )


def _validate_adjective_layout(table: TableData) -> None:
    require_adjective_layout(table.adjective_table_layout)


def _validate_adjective_table(table: TableData) -> None:
    """Validate an adjective pair table: a known layout and 8 columns/cells."""
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


TABLE_VALIDATORS: dict[str, Callable[[TableData], None]] = {
    "noun": _validate_noun_table,
    "adjective_layout": _validate_adjective_layout,
    "adjective_pair": _validate_adjective_table,
    "adjective_other": _validate_adjective_other_table,
}


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


def is_special_topic_adjective_rule(
    rule_name: str | None,
    rule_description: str | None,
    *,
    topic_stems: tuple[str, ...] | None = None,
) -> bool:
    """Whether rule text matches a configured special adjective topic."""
    if topic_stems is None:
        policy = CATEGORY_CONFIG["adjective"].special_topic
        if policy is None:
            return False
        topic_stems = policy.topic_stems
    source = f"{rule_name or ''} {rule_description or ''}".casefold()
    words = re.findall(r"[a-z]+", source)
    return any(
        word.startswith(stem)
        for word in words
        for stem in topic_stems
    )


def _matches_special_topic(
    state: GenerateTableState, policy: SpecialTopicPolicy
) -> bool:
    target_language = (state.get("target_language") or "").strip().casefold()
    if target_language not in policy.target_languages:
        return False
    return is_special_topic_adjective_rule(
        state.get("rule_name"),
        state.get("rule_description"),
        topic_stems=policy.topic_stems,
    )


def _invoke_table_prompt(
    prompt: BasePromptTemplate,
    state: GenerateTableState,
    additional_prompt_variables: dict[str, str] | None = None,
) -> TableData:
    chain = prompt | llm.with_structured_output(TableData)
    return chain.invoke({
        "native_language": state["native_language"],
        "target_language": state["target_language"],
        "rule_name": state["rule_name"],
        "rule_description": state["rule_description"] or "",
        **(additional_prompt_variables or {}),
    })


def _run_validator(table: TableData, validator_name: str | None) -> None:
    if validator_name is None:
        return
    try:
        validator = TABLE_VALIDATORS[validator_name]
    except KeyError as error:
        raise ValueError(
            f"Unknown table validator configured: {validator_name}"
        ) from error
    validator(table)


def _generate_from_prompt_roles(
    state: GenerateTableState, config: CategoryConfig
) -> tuple[TableData, ...]:
    if config.special_topic and _matches_special_topic(state, config.special_topic):
        prompt = config.prompt_roles[config.special_topic.prompt_role]
        table = _invoke_table_prompt(prompt, state)
        _run_validator(table, config.special_topic.validator)
        return (table,)

    if config.entry_prompt_role is None:
        raise ValueError("Category prompt roles require an entry prompt role")
    entry_table = _invoke_table_prompt(
        config.prompt_roles[config.entry_prompt_role], state
    )

    if config.layout_field is None:
        raise ValueError("Category prompt roles require a layout field")
    layout = getattr(entry_table, config.layout_field)
    route = config.layout_routes.get(str(layout))
    if route is None:
        _run_validator(entry_table, config.layout_validator)
        raise ValueError(f"No generation route configured for table layout: {layout}")

    _run_validator(entry_table, route.validator)
    tables = [entry_table]
    if route.companion_prompt_role is not None:
        additional_prompt_variables: dict[str, str] = {}
        if route.companion_context == "avoid_carrier_phrases":
            additional_prompt_variables = {
                "avoid_phrases": ", ".join(_used_carrier_phrases(entry_table))
            }
        elif route.companion_context is not None:
            raise ValueError(
                "Unknown companion prompt context configured: "
                f"{route.companion_context}"
            )
        companion_prompt = config.prompt_roles[route.companion_prompt_role]
        companion_table = _invoke_table_prompt(
            companion_prompt, state, additional_prompt_variables
        )
        _run_validator(
            companion_table,
            route.companion_validator or route.validator,
        )
        tables.append(companion_table)
    return tuple(tables)


def _generate_tables(
    state: GenerateTableState, config: CategoryConfig
) -> tuple[TableData, ...]:
    if config.prompt is not None:
        table = _invoke_table_prompt(config.prompt, state)
        _run_validator(table, config.validator)
        return (table,)
    if config.prompt_roles:
        return _generate_from_prompt_roles(state, config)
    raise ValueError("Category configuration has no prompt")


def generate_category_table_node(state: GenerateTableState) -> GenerateTableState:
    slug = state.get("word_category_slug")
    config = CATEGORY_CONFIG.get(slug)
    if config is None:
        config = CategoryConfig(prompt=generate_table_prompt)

    tables = _generate_tables(state, config)
    return {
        **state,
        "general_tables": [table.model_dump() for table in tables],
    }
