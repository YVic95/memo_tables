from graphs.llm import llm
from graphs.models import DeducedBaseWords
from graphs.prompts import deduce_base_word_prompt
from graphs.states import SaveTableState
from graphs.table_utils import (
    NOUN_SIDE_COLUMNS,
    NounTableLayout,
    cell_at_role,
    column_roles,
    noun_side_cell,
    require_noun_layout,
    role_to_column,
    tokenize_words,
)
from crud.rules import get_grammar_rule_by_id, get_word_categories, get_word_category_by_id
from crud.language_pairs import get_language_name_by_id

deduce_llm = llm.with_structured_output(DeducedBaseWords)
deduce_chain = deduce_base_word_prompt | deduce_llm


def _extract_unique_forms(tables: list[dict]) -> list[str]:
    forms: set[str] = set()
    for table in tables:
        for row in table.get("rows", []):
            for cell in row.get("cells", []):
                stripped = cell.strip()
                if stripped:
                    forms.add(stripped)
    return sorted(forms)


def _extract_forms_by_role(
    tables: list[dict], role_lookup: dict[str, int], role: str
) -> list[str]:
    forms: set[str] = set()
    for table in tables:
        for row in table.get("rows", []):
            cell = cell_at_role(row.get("cells", []), role_lookup, role)
            if cell is not None and cell.strip():
                forms.add(cell.strip())
    return sorted(forms)


def _extract_form_cells(tables: list[dict], role_lookup: dict[str, int]) -> list[str]:
    return _extract_forms_by_role(tables, role_lookup, "form")


def _extract_example_words(tables: list[dict], role_lookup: dict[str, int]) -> list[str]:
    words: set[str] = set()
    for table in tables:
        for row in table.get("rows", []):
            example = cell_at_role(row.get("cells", []), role_lookup, "example")
            if example:
                words.update(token.lower() for token in tokenize_words(example))
    return sorted(words)


def _noun_base_words_and_translations(
    tables: list[dict],
    language_id,
    word_category_id,
):
    """Build noun base words directly from the paired form/translation cells.

    Number tables contribute one base word per pair, using the singular side as
    the dictionary form and keeping the plural as a surface form. Gender tables
    contribute both the masculine and the feminine noun as separate base words.
    """
    base_words: dict[str, dict] = {}
    translations: dict[str, str] = {}

    def add(form: str, surface_forms: list[str], translation: str) -> None:
        if not form:
            return
        key = form.lower()
        entry = base_words.setdefault(
            key,
            {
                "text": form,
                "language_id": language_id,
                "word_category_id": word_category_id,
                "forms": set(),
            },
        )
        entry["forms"].update(form.lower() for form in surface_forms if form)
        if translation and key not in translations:
            translations[key] = translation

    for table in tables:
        layout = require_noun_layout(table.get("noun_table_layout"))

        for row in table.get("rows", []):
            cells = row.get("cells", [])
            singular_or_masculine = NOUN_SIDE_COLUMNS[0]
            plural_or_feminine = NOUN_SIDE_COLUMNS[1]
            singular_or_masculine_form = noun_side_cell(cells, singular_or_masculine, "form")
            plural_or_feminine_form = noun_side_cell(cells, plural_or_feminine, "form")
            singular_or_masculine_translation = noun_side_cell(
                cells, singular_or_masculine, "translation"
            )
            plural_or_feminine_translation = noun_side_cell(
                cells, plural_or_feminine, "translation"
            )

            if layout is NounTableLayout.noun_number:
                if singular_or_masculine_form:
                    add(
                        singular_or_masculine_form,
                        [singular_or_masculine_form, plural_or_feminine_form],
                        singular_or_masculine_translation,
                    )
                elif plural_or_feminine_form:
                    add(
                        plural_or_feminine_form,
                        [plural_or_feminine_form],
                        plural_or_feminine_translation,
                    )
                continue

            if singular_or_masculine_form:
                add(
                    singular_or_masculine_form,
                    [singular_or_masculine_form],
                    singular_or_masculine_translation,
                )
            if plural_or_feminine_form:
                add(
                    plural_or_feminine_form,
                    [plural_or_feminine_form],
                    plural_or_feminine_translation,
                )

    result = []
    for entry in base_words.values():
        result.append(
            {
                "text": entry["text"],
                "language_id": entry["language_id"],
                "word_category_id": entry["word_category_id"],
                "forms": sorted(entry["forms"]),
            }
        )

    return (
        sorted(result, key=lambda base_word: base_word["text"].lower()),
        {base_words[key]["text"]: value for key, value in translations.items()},
    )


def deduce_base_word_node(state: SaveTableState) -> SaveTableState:
    is_verb = state["word_category_slug"] == "verb"
    is_noun = state["word_category_slug"] == "noun"

    rule = get_grammar_rule_by_id(state["db"], state["grammar_rule_id"])
    if rule is None:
        raise ValueError(f"Grammar rule {state['grammar_rule_id']} not found")

    if is_noun:
        base_words, translations = _noun_base_words_and_translations(
            state["tables"],
            state["target_language_id"],
            rule.word_category_id,
        )
        return {
            **state,
            "base_words_to_save": base_words,
            "base_word_translations": translations,
        }

    role_lookup = role_to_column(column_roles(state["word_category_slug"]))

    if is_verb:
        unique_forms = sorted(
            set(_extract_form_cells(state["tables"], role_lookup))
            | set(_extract_example_words(state["tables"], role_lookup))
        )
    else:
        unique_forms = _extract_unique_forms(state["tables"])

    if not unique_forms:
        return {
            **state,
            "base_words_to_save": [],
        }

    rule_category = get_word_category_by_id(state["db"], rule.word_category_id)
    categories = get_word_categories(state["db"])
    valid_category_ids = {category.id for category in categories}
    rule_word_category = (
        f"{rule_category.id}: {rule_category.name} ({rule_category.slug})"
    )

    target_language_name = get_language_name_by_id(state["db"], state["target_language_id"])

    chain_input = {
        "target_language": target_language_name,
        "rule_word_category": rule_word_category,
        "surface_forms": "\n".join(unique_forms),
    }
    chain_input["available_categories"] = "\n".join(
        f"{category.id}: {category.name} ({category.slug})" for category in categories
    )

    result: DeducedBaseWords = deduce_chain.invoke(chain_input)

    base_words = []
    for base_word in result.base_words:
        word_category_id = base_word.word_category_id
        if word_category_id not in valid_category_ids or not is_verb:
            word_category_id = rule.word_category_id
        base_words.append(
            {
                "text": base_word.word,
                "language_id": state["target_language_id"],
                "word_category_id": word_category_id,
                "forms": [form.lower() for form in base_word.surface_forms],
            }
        )

    return {
        **state,
        "base_words_to_save": base_words,
    }
