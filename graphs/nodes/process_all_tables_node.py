from graphs.llm import llm
from graphs.models import Translations
from graphs.prompts import translate_words_prompt
from graphs.states import SaveTableState
from graphs.table_utils import column_roles, role_to_column, cell_at_role, tokenize_words
from crud.language_pairs import get_language_name_by_id
from crud.rules import get_grammar_rule_by_id
from crud.table_data import (
    create_grammar_rule_row,
    create_grammar_rule_row_translation,
    create_sentence,
    create_sentence_translation,
    create_word_form_sentence,
    get_or_create_word_form,
    get_or_create_word_form_global,
    get_or_create_word_form_translation,
    get_or_create_word_rule_assignment,
)

translate_llm = llm.with_structured_output(Translations)
translate_chain = translate_words_prompt | translate_llm


def _collect_translation_strings(state: SaveTableState) -> set[str]:
    strings: set[str] = set()
    body_roles = ("label", "form", "example")
    is_verb = state["word_category_slug"] == "verb"
    role_lookup = role_to_column(column_roles(state["word_category_slug"]))
    for table in state["tables"]:
        for row in table.get("rows", []):
            cells = row.get("cells", [])
            for role in body_roles:
                cell = cell_at_role(cells, role_lookup, role)
                if cell is not None and cell.strip():
                    strings.add(cell)
            if is_verb:
                example = cell_at_role(cells, role_lookup, "example")
                if example:
                    strings.update(token.lower() for token in tokenize_words(example))
    return strings


def _word_form_for_surface_form(
    db,
    form_to_base_word_id: dict[str, object],
    grammar_rule_id,
    surface_form: str,
    grammar_row_id,
):
    base_word_id = form_to_base_word_id.get(surface_form.lower())
    if base_word_id is None:
        return None
    assignment = get_or_create_word_rule_assignment(db, base_word_id, grammar_rule_id, commit=False)
    return get_or_create_word_form(db, assignment.id, grammar_row_id, surface_form, commit=False)


def process_all_tables_node(state: SaveTableState) -> SaveTableState:
    db = state["db"]
    grammar_rule_id = state["grammar_rule_id"]
    native_language_id = state["native_language_id"]
    target_language_id = state["target_language_id"]
    form_to_base_word_id = state["form_to_base_word_id"]
    is_verb = state["word_category_slug"] == "verb"

    rule = get_grammar_rule_by_id(db, grammar_rule_id)
    if rule is None:
        raise ValueError(f"Grammar rule {grammar_rule_id} not found")

    role_lookup = role_to_column(column_roles(state["word_category_slug"]))

    translation_strings = _collect_translation_strings(state)
    translations: dict[str, str] = {}
    if translation_strings:
        target_language_name = get_language_name_by_id(db, target_language_id)
        native_language_name = get_language_name_by_id(db, native_language_id)
        result: Translations = translate_chain.invoke(
            {
                "target_language": target_language_name,
                "native_language": native_language_name,
                "items": "\n".join(sorted(translation_strings)),
            }
        )
        translations = {item.text.strip(): item.translation for item in result.translations}

    for table in state["tables"]:
        table_no = table.get("fragmented_table_id") or 0

        for index, row in enumerate(table.get("rows", [])):
            cells = row.get("cells", [])
            position = row.get("row_position")
            if position is None:
                position = index

            label = cell_at_role(cells, role_lookup, "label") or ""
            explanation = cell_at_role(cells, role_lookup, "explanation")
            form = cell_at_role(cells, role_lookup, "form")
            example = cell_at_role(cells, role_lookup, "example")

            grammar_row = create_grammar_rule_row(
                db,
                grammar_rule_id,
                label,
                explanation,
                table_no,
                position,
                commit=False,
            )
            create_grammar_rule_row_translation(
                db,
                grammar_row.id,
                native_language_id,
                translations.get(label, label),
                explanation,
                commit=False,
            )

            verb_word_form = None
            if form is not None and form.strip():
                verb_word_form = _word_form_for_surface_form(
                    db, form_to_base_word_id, grammar_rule_id, form, grammar_row.id
                )
                if verb_word_form is not None:
                    get_or_create_word_form_translation(
                        db,
                        verb_word_form.id,
                        native_language_id,
                        translations.get(form, form),
                        commit=False,
                    )

            if example is not None and example.strip():
                sentence = create_sentence(
                    db,
                    example,
                    target_language_id,
                    rule.word_category_id,
                    grammar_rule_id,
                    position,
                    commit=False,
                )
                create_sentence_translation(
                    db,
                    sentence.id,
                    native_language_id,
                    translations.get(example, example),
                    commit=False,
                )

                if verb_word_form is not None:
                    create_word_form_sentence(db, verb_word_form.id, sentence.id, commit=False)

                if is_verb:
                    for token in tokenize_words(example):
                        token = token.lower()
                        if not token:
                            continue
                        if form is not None and token == form.lower():
                            continue
                        token_base_word_id = form_to_base_word_id.get(token)
                        if token_base_word_id is None:
                            continue
                        assignment = get_or_create_word_rule_assignment(
                            db, token_base_word_id, grammar_rule_id, commit=False
                        )
                        token_word_form = get_or_create_word_form_global(
                            db, assignment.id, token, grammar_row.id, commit=False
                        )
                        if token_word_form is None:
                            continue
                        get_or_create_word_form_translation(
                            db,
                            token_word_form.id,
                            native_language_id,
                            translations.get(token, token),
                            commit=False,
                        )
                        create_word_form_sentence(db, token_word_form.id, sentence.id, commit=False)

    return state