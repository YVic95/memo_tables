from graphs.states import SaveTableState
from crud.table_data import (
    get_or_create_base_word,
    get_or_create_word_rule_assignment,
)


def save_base_word_node(state: SaveTableState) -> SaveTableState:
    db = state["db"]
    form_to_base_word_id: dict[str, object] = {}

    for base_word in state["base_words_to_save"]:
        word = get_or_create_base_word(
            db,
            base_word["text"],
            base_word["language_id"],
            base_word["word_category_id"],
            commit=False,
        )
        get_or_create_word_rule_assignment(
            db,
            word.id,
            state["grammar_rule_id"],
            commit=False,
        )
        for form in base_word.get("forms", []):
            form_to_base_word_id[form.lower()] = word.id

    return {
        **state,
        "form_to_base_word_id": form_to_base_word_id,
    }