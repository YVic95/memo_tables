from sqlalchemy.orm import Session
from models.base_words import BaseWord
from models.word_translations import WordTranslation
from models.word_rule_assignments import WordRuleAssignment
from models.grammar_rule_rows import GrammarRuleRow
from models.grammar_rule_row_translations import GrammarRuleRowTranslation
from models.word_forms import WordForm
from models.word_form_translations import WordFormTranslation
from models.sentences import Sentence
from models.sentence_translations import SentenceTranslation
from models.word_form_sentences import WordFormSentence


def get_or_create_base_word(
    db: Session,
    text: str,
    language_id: str,
    word_category_id: str,
) -> BaseWord:
    existing = (
        db.query(BaseWord)
        .filter(
            BaseWord.text == text,
            BaseWord.language_id == language_id,
            BaseWord.word_category_id == word_category_id,
        )
        .first()
    )
    if existing is not None:
        return existing

    word = BaseWord(
        text=text,
        language_id=language_id,
        word_category_id=word_category_id,
    )
    db.add(word)
    db.commit()
    db.refresh(word)
    return word


def create_word_translation(
    db: Session,
    base_word_id: str,
    language_id: str,
    translation: str,
) -> WordTranslation:
    word_translation = WordTranslation(
        base_word_id=base_word_id,
        language_id=language_id,
        translation=translation,
    )
    db.add(word_translation)
    db.commit()
    db.refresh(word_translation)
    return word_translation


def create_word_rule_assignment(
    db: Session,
    base_word_id: str,
    grammar_rule_id: str,
) -> WordRuleAssignment:
    word_rule_assignment = WordRuleAssignment(
        base_word_id=base_word_id,
        grammar_rule_id=grammar_rule_id,
    )
    db.add(word_rule_assignment)
    db.commit()
    db.refresh(word_rule_assignment)
    return word_rule_assignment


def create_grammar_rule_row(
    db: Session,
    grammar_rule_id: str,
    label: str,
    description: str | None,
    table_no: int,
    position: int,
) -> GrammarRuleRow:
    row = GrammarRuleRow(
        grammar_rule_id=grammar_rule_id,
        label=label,
        description=description,
        table_no=table_no,
        position=position,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_grammar_rule_row_translation(
    db: Session,
    grammar_rule_row_id: str,
    language_id: str,
    label_translation: str,
    description_translation: str | None,
) -> GrammarRuleRowTranslation:
    translation = GrammarRuleRowTranslation(
        grammar_rule_row_id=grammar_rule_row_id,
        language_id=language_id,
        label_translation=label_translation,
        description_translation=description_translation,
    )
    db.add(translation)
    db.commit()
    db.refresh(translation)
    return translation


def create_word_form(
    db: Session,
    word_rule_assignment_id: str,
    grammar_rule_row_id: str,
    form: str,
) -> WordForm:
    word_form = WordForm(
        word_rule_assignment_id=word_rule_assignment_id,
        grammar_rule_row_id=grammar_rule_row_id,
        form=form,
    )
    db.add(word_form)
    db.commit()
    db.refresh(word_form)
    return word_form


def create_word_form_translation(
    db: Session,
    word_form_id: str,
    language_id: str,
    translation: str,
) -> WordFormTranslation:
    word_form_translation = WordFormTranslation(
        word_form_id=word_form_id,
        language_id=language_id,
        translation=translation,
    )
    db.add(word_form_translation)
    db.commit()
    db.refresh(word_form_translation)
    return word_form_translation


def create_sentence(
    db: Session,
    template: str,
    language_id: str,
    word_category_id: str,
    grammar_rule_id: str,
    row_position: int,
) -> Sentence:
    sentence = Sentence(
        template=template,
        language_id=language_id,
        word_category_id=word_category_id,
        grammar_rule_id=grammar_rule_id,
        row_position=row_position,
    )
    db.add(sentence)
    db.commit()
    db.refresh(sentence)
    return sentence


def create_sentence_translation(
    db: Session,
    sentence_id: str,
    language_id: str,
    template: str,
) -> SentenceTranslation:
    sentence_translation = SentenceTranslation(
        sentence_id=sentence_id,
        language_id=language_id,
        template=template,
    )
    db.add(sentence_translation)
    db.commit()
    db.refresh(sentence_translation)
    return sentence_translation


def create_word_form_sentence(
    db: Session,
    word_form_id: str,
    sentence_id: str,
) -> WordFormSentence:
    word_form_sentence = WordFormSentence(
        word_form_id=word_form_id,
        sentence_id=sentence_id,
    )
    db.add(word_form_sentence)
    db.commit()
    db.refresh(word_form_sentence)
    return word_form_sentence
