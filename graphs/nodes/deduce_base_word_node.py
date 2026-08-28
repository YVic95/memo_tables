from graphs.llm import llm
from graphs.models import DeducedBaseWords
from graphs.prompts import deduce_base_word_prompt
from graphs.states import SaveTableState
from graphs.table_utils import column_roles, role_to_column, cell_at_role, tokenize_words
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


def _extract_verb_forms(tables: list[dict], role_lookup: dict[str, int]) -> list[str]:
    forms: set[str] = set()
    for table in tables:
        for row in table.get("rows", []):
            cell = cell_at_role(row.get("cells", []), role_lookup, "form")
            if cell is not None and cell.strip():
                forms.add(cell.strip())
    return sorted(forms)


def _extract_example_words(tables: list[dict], role_lookup: dict[str, int]) -> list[str]:
    words: set[str] = set()
    for table in tables:
        for row in table.get("rows", []):
            example = cell_at_role(row.get("cells", []), role_lookup, "example")
            if example:
                words.update(token.lower() for token in tokenize_words(example))
    return sorted(words)


def deduce_base_word_node(state: SaveTableState) -> SaveTableState:
    is_verb = state["word_category_slug"] == "verb"
    role_lookup = role_to_column(column_roles(state["word_category_slug"]))

    if is_verb:
        unique_forms = sorted(
            set(_extract_verb_forms(state["tables"], role_lookup))
            | set(_extract_example_words(state["tables"], role_lookup))
        )
    else:
        unique_forms = _extract_unique_forms(state["tables"])

    if not unique_forms:
        return {
            **state,
            "base_words_to_save": [],
        }

    rule = get_grammar_rule_by_id(state["db"], state["grammar_rule_id"])
    if rule is None:
        raise ValueError(f"Grammar rule {state['grammar_rule_id']} not found")

    rule_category = get_word_category_by_id(state["db"], rule.word_category_id)
    categories = get_word_categories(state["db"])
    valid_category_ids = {category.id for category in categories}
    available_categories = "\n".join(
        f"{category.id}: {category.name} ({category.slug})" for category in categories
    )
    rule_word_category = (
        f"{rule_category.id}: {rule_category.name} ({rule_category.slug})"
    )

    target_language_name = get_language_name_by_id(state["db"], state["target_language_id"])

    result: DeducedBaseWords = deduce_chain.invoke(
        {
            "target_language": target_language_name,
            "available_categories": available_categories,
            "rule_word_category": rule_word_category,
            "surface_forms": "\n".join(unique_forms),
        }
    )

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
                "translation": base_word.native_translation,
                "forms": [form.lower() for form in base_word.surface_forms],
            }
        )

    return {
        **state,
        "base_words_to_save": base_words,
    }