from graphs.llm import llm
from graphs.models import DeducedBaseWord, DeducedBaseWords
from graphs.noun_forms import citation_candidates, is_singular_definite, noun_keys, singular_form
from graphs.prompts import deduce_base_word_prompt, deduce_noun_base_word_prompt
from graphs.states import SaveTableState
from graphs.table_utils import column_roles, role_to_column, cell_at_role, tokenize_words
from crud.rules import get_grammar_rule_by_id, get_word_categories, get_word_category_by_id
from crud.language_pairs import get_language_name_by_id

deduce_llm = llm.with_structured_output(DeducedBaseWords)
deduce_chain = deduce_base_word_prompt | deduce_llm
deduce_noun_chain = deduce_noun_base_word_prompt | deduce_llm


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


def _group_noun_base_words(
    deduced_base_words: list[DeducedBaseWord],
    form_cells: list[str],
    language_name: str,
    word_category_id,
) -> list[DeducedBaseWord]:
    """Collapse model output and form cells into one base word per noun.

    The model may return one entry per surface form, or omit a form entirely.
    Grouping by a normalized key and preferring the singular definite form makes
    the persisted vocabulary deterministic regardless of which shape the model
    returns.
    """
    groups: list[dict] = []

    def group_for(text: str) -> dict:
        keys = noun_keys(text, language_name)
        matching_groups = [group for group in groups if group["keys"] & keys]
        if not matching_groups:
            group = {"keys": keys, "candidates": [], "forms": set()}
            groups.append(group)
            return group

        group = matching_groups[0]
        group["keys"] |= keys
        for other_group in matching_groups[1:]:
            group["keys"] |= other_group["keys"]
            group["candidates"].extend(other_group["candidates"])
            group["forms"] |= other_group["forms"]
            groups.remove(other_group)
        return group

    for base_word in deduced_base_words:
        group = group_for(base_word.word)
        priority = 0 if is_singular_definite(base_word.word, language_name) else 3
        group["candidates"].append((priority, base_word.word.lower()))
        group["forms"].update(form.lower() for form in base_word.surface_forms)

    for form in form_cells:
        group = group_for(form)
        group["forms"].add(form.lower())
        if is_singular_definite(form, language_name):
            group["candidates"].append((0, form.lower()))
            continue

        candidates = citation_candidates(form, language_name)
        if not candidates:
            group["candidates"].append((4, singular_form(form, language_name)))
            continue

        group["candidates"].extend(
            (priority + 1, citation) for priority, citation in candidates
        )

    grouped_base_words = []
    for group in groups:
        if not group["candidates"]:
            continue
        citation = min(group["candidates"])[1]
        grouped_base_words.append(
            DeducedBaseWord(
                word=citation,
                word_category_id=word_category_id,
                surface_forms=sorted(group["forms"]),
            )
        )

    return sorted(grouped_base_words, key=lambda base_word: base_word.word)


def deduce_base_word_node(state: SaveTableState) -> SaveTableState:
    is_verb = state["word_category_slug"] == "verb"
    is_noun = state["word_category_slug"] == "noun"
    role_lookup = role_to_column(column_roles(state["word_category_slug"]))

    if is_verb:
        unique_forms = sorted(
            set(_extract_form_cells(state["tables"], role_lookup))
            | set(_extract_example_words(state["tables"], role_lookup))
        )
        chain = deduce_chain
    elif is_noun:
        unique_forms = _extract_form_cells(state["tables"], role_lookup)
        chain = deduce_noun_chain
    else:
        unique_forms = _extract_unique_forms(state["tables"])
        chain = deduce_chain

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
    rule_word_category = (
        f"{rule_category.id}: {rule_category.name} ({rule_category.slug})"
    )

    target_language_name = get_language_name_by_id(state["db"], state["target_language_id"])

    chain_input = {
        "target_language": target_language_name,
        "rule_word_category": rule_word_category,
        "surface_forms": "\n".join(unique_forms),
    }
    if not is_noun:
        chain_input["available_categories"] = "\n".join(
            f"{category.id}: {category.name} ({category.slug})" for category in categories
        )

    result: DeducedBaseWords = chain.invoke(chain_input)

    deduced_base_words = result.base_words
    if is_noun:
        deduced_base_words = _group_noun_base_words(
            deduced_base_words,
            unique_forms,
            target_language_name,
            rule.word_category_id,
        )

    base_words = []
    for base_word in deduced_base_words:
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