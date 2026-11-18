from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from langchain_core.prompts import BasePromptTemplate

from graphs.models import TableData
from graphs.prompts import (
    choose_adjective_table_prompt,
    generate_adjective_gender_or_agreement_table_prompt,
    generate_adjective_number_table_prompt,
    generate_adjective_other_table_prompt,
    generate_noun_table_prompt,
    generate_verb_table_prompt,
)
from graphs.states import GenerateTableState
from graphs.table_utils import ADJECTIVE_SIDE_COLUMNS
from graphs.table_validators import (
    validate_adjective_other_table,
    validate_adjective_pair_table,
    validate_noun_table,
)

TableValidator = Callable[[TableData], None]
CompanionContext = Callable[[TableData], dict[str, str]]
ClassifierInput = Callable[[GenerateTableState], dict[str, str]]


@dataclass(frozen=True)
class LayoutPolicy:
    """Generation and validation policy for one declared table layout."""

    prompt_role: str | None = None
    validator: TableValidator | None = None
    companion_prompt_role: str | None = None
    companion_context: CompanionContext | None = None
    companion_validator: TableValidator | None = None


@dataclass(frozen=True)
class CategoryConfig:
    """Prompt and table-generation policy for one word category."""

    prompt: BasePromptTemplate | None = None
    validator: TableValidator | None = None
    prompt_roles: Mapping[str, BasePromptTemplate] = field(default_factory=dict)
    classifier_prompt: BasePromptTemplate | None = None
    classifier_input: ClassifierInput | None = None
    entry_prompt_role: str | None = None
    layout_field: str | None = None
    layout_validator: TableValidator | None = None
    layout_routes: Mapping[str, LayoutPolicy] = field(default_factory=dict)


def used_carrier_phrases(number_table: TableData) -> list[str]:
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
        key = phrase.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(phrase)
    return unique


def avoid_carrier_phrases_context(entry_table: TableData) -> dict[str, str]:
    return {"avoid_phrases": ", ".join(used_carrier_phrases(entry_table))}


def adjective_rule_text(state: GenerateTableState) -> dict[str, str]:
    return {
        "rule_name": state.get("rule_name") or "",
        "rule_description": state.get("rule_description") or "",
    }


CATEGORY_CONFIG: dict[str, CategoryConfig] = {
    "verb": CategoryConfig(prompt=generate_verb_table_prompt),
    "noun": CategoryConfig(
        prompt=generate_noun_table_prompt,
        validator=validate_noun_table,
    ),
    "adjective": CategoryConfig(
        prompt_roles={
            "number": generate_adjective_number_table_prompt,
            "gender_or_agreement": generate_adjective_gender_or_agreement_table_prompt,
            "other": generate_adjective_other_table_prompt,
        },
        classifier_prompt=choose_adjective_table_prompt,
        classifier_input=adjective_rule_text,
        layout_field="adjective_table_layout",
        layout_routes={
            "adj_number_gender": LayoutPolicy(
                prompt_role="number",
                validator=validate_adjective_pair_table,
                companion_prompt_role="gender_or_agreement",
                companion_context=avoid_carrier_phrases_context,
                companion_validator=validate_adjective_pair_table,
            ),
            "adj_agreement": LayoutPolicy(
                prompt_role="gender_or_agreement",
                validator=validate_adjective_pair_table,
            ),
            "adj_other": LayoutPolicy(
                prompt_role="other",
                validator=validate_adjective_other_table,
            ),
        },
    ),
}
