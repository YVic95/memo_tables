from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from langchain_core.prompts import BasePromptTemplate

from graphs.models import TableData
from graphs.prompts import (
    choose_adjective_table_prompt,
    generate_adjective_gender_table_prompt,
    generate_adjective_gender_or_agreement_table_prompt,
    generate_adjective_number_table_prompt,
    generate_adjective_other_table_prompt,
    generate_noun_table_prompt,
    generate_verb_table_prompt,
)
from graphs.states import GenerateTableState
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
    companion_layout: str | None = None
    # Layout the entry table must carry. Defaults to the route key; set when
    # one classifier choice fans out to tables with different layouts
    # (agreement: choice "adj_agreement", entry "adj_agreement_number").
    entry_layout: str | None = None


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


def adjective_rule_text(state: GenerateTableState) -> dict[str, str]:
    return {
        "rule_name": state.get("rule_name") or "",
        "rule_description": state.get("rule_description") or "",
    }


def adjective_avoid_phrases(entry_table: TableData) -> dict[str, str]:
    """Form-cell phrases of the entry table, to keep the companion fresh.

    The agreement by-gender prompt receives these as {avoid_phrases}
    and must choose different adjectives and carrier nouns.
    """
    phrases: list[str] = []
    for row in entry_table.rows:
        for index in (0, 4):
            if index < len(row.cells):
                phrase = (row.cells[index] or "").replace("*", "").strip()
                if phrase:
                    phrases.append(phrase)
    seen: set[str] = set()
    unique: list[str] = []
    for phrase in phrases:
        key = phrase.lower()
        if key not in seen:
            seen.add(key)
            unique.append(phrase)
    return {"avoid_phrases": ", ".join(unique)}


CATEGORY_CONFIG: dict[str, CategoryConfig] = {
    "verb": CategoryConfig(prompt=generate_verb_table_prompt),
    "noun": CategoryConfig(
        prompt=generate_noun_table_prompt,
        validator=validate_noun_table,
    ),
    "adjective": CategoryConfig(
        prompt_roles={
            "number": generate_adjective_number_table_prompt,
            "gender": generate_adjective_gender_table_prompt,
            "gender_or_agreement": generate_adjective_gender_or_agreement_table_prompt,
            "other": generate_adjective_other_table_prompt,
        },
        classifier_prompt=choose_adjective_table_prompt,
        classifier_input=adjective_rule_text,
        layout_field="adjective_table_layout",
        layout_routes={
            "adj_number": LayoutPolicy(
                prompt_role="number",
                validator=validate_adjective_pair_table,
            ),
            "adj_gender": LayoutPolicy(
                prompt_role="gender",
                validator=validate_adjective_pair_table,
            ),
            "adj_agreement": LayoutPolicy(
                prompt_role="number",
                validator=validate_adjective_pair_table,
                companion_prompt_role="gender_or_agreement",
                companion_context=adjective_avoid_phrases,
                companion_validator=validate_adjective_pair_table,
                companion_layout="adj_agreement_gender",
                entry_layout="adj_agreement_number",
            ),
            "adj_other": LayoutPolicy(
                prompt_role="other",
                validator=validate_adjective_other_table,
            ),
        },
    ),
}
