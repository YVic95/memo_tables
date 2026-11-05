from graphs.llm import llm
from graphs.models import Translations
from graphs.prompts import translate_base_words_prompt
from graphs.states import SaveTableState
from crud.language_pairs import get_language_name_by_id

translate_llm = llm.with_structured_output(Translations)
translate_chain = translate_base_words_prompt | translate_llm


def translate_base_words_node(state: SaveTableState) -> SaveTableState:
    base_words = state.get("base_words_to_save", [])
    if not base_words:
        return {
            **state,
            "base_word_translations": {},
        }

    translations = dict(state.get("base_word_translations") or {})
    unique_texts = sorted({word["text"] for word in base_words})
    missing_texts = [text for text in unique_texts if not translations.get(text)]

    if not missing_texts:
        return {
            **state,
            "base_word_translations": translations,
        }

    target_language_name = get_language_name_by_id(state["db"], state["target_language_id"])
    native_language_name = get_language_name_by_id(state["db"], state["native_language_id"])

    result: Translations = translate_chain.invoke(
        {
            "target_language": target_language_name,
            "native_language": native_language_name,
            "items": "\n".join(missing_texts),
        }
    )

    translations.update(
        {item.text.strip(): item.translation for item in result.translations}
    )

    return {
        **state,
        "base_word_translations": translations,
    }
