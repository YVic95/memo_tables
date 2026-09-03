import uuid
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


def _commit_or_flush(db: Session, commit: bool) -> None:
    if commit:
        db.commit()
    else:
        db.flush()


def get_or_create_base_word(
    db: Session,
    text: str,
    language_id: uuid.UUID,
    word_category_id: uuid.UUID,
    commit: bool = True,
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
    _commit_or_flush(db, commit)
    db.refresh(word)
    return word


def create_word_translation(
    db: Session,
    base_word_id: uuid.UUID,
    language_id: uuid.UUID,
    translation: str,
    commit: bool = True,
) -> WordTranslation:
    word_translation = WordTranslation(
        base_word_id=base_word_id,
        language_id=language_id,
        translation=translation,
    )
    db.add(word_translation)
    _commit_or_flush(db, commit)
    db.refresh(word_translation)
    return word_translation


def get_or_create_word_translation(
    db: Session,
    base_word_id: uuid.UUID,
    language_id: uuid.UUID,
    translation: str,
    commit: bool = True,
) -> WordTranslation:
    existing = (
        db.query(WordTranslation)
        .filter(
            WordTranslation.base_word_id == base_word_id,
            WordTranslation.language_id == language_id,
        )
        .first()
    )
    if existing is not None:
        return existing
    return create_word_translation(db, base_word_id, language_id, translation, commit=commit)


def create_word_rule_assignment(
    db: Session,
    base_word_id: uuid.UUID,
    grammar_rule_id: uuid.UUID,
    commit: bool = True,
) -> WordRuleAssignment:
    word_rule_assignment = WordRuleAssignment(
        base_word_id=base_word_id,
        grammar_rule_id=grammar_rule_id,
    )
    db.add(word_rule_assignment)
    _commit_or_flush(db, commit)
    db.refresh(word_rule_assignment)
    return word_rule_assignment


def get_or_create_word_rule_assignment(
    db: Session,
    base_word_id: uuid.UUID,
    grammar_rule_id: uuid.UUID,
    commit: bool = True,
) -> WordRuleAssignment:
    existing = (
        db.query(WordRuleAssignment)
        .filter(
            WordRuleAssignment.base_word_id == base_word_id,
            WordRuleAssignment.grammar_rule_id == grammar_rule_id,
        )
        .first()
    )
    if existing is not None:
        return existing
    return create_word_rule_assignment(db, base_word_id, grammar_rule_id, commit=commit)


def create_grammar_rule_row(
    db: Session,
    grammar_rule_id: uuid.UUID,
    label: str,
    description: str | None,
    table_no: int,
    position: int,
    commit: bool = True,
) -> GrammarRuleRow:
    row = GrammarRuleRow(
        grammar_rule_id=grammar_rule_id,
        label=label,
        description=description,
        table_no=table_no,
        position=position,
    )
    db.add(row)
    _commit_or_flush(db, commit)
    db.refresh(row)
    return row


def create_grammar_rule_row_translation(
    db: Session,
    grammar_rule_row_id: uuid.UUID,
    language_id: uuid.UUID,
    label_translation: str,
    description_translation: str | None,
    commit: bool = True,
) -> GrammarRuleRowTranslation:
    translation = GrammarRuleRowTranslation(
        grammar_rule_row_id=grammar_rule_row_id,
        language_id=language_id,
        label_translation=label_translation,
        description_translation=description_translation,
    )
    db.add(translation)
    _commit_or_flush(db, commit)
    db.refresh(translation)
    return translation


def create_word_form(
    db: Session,
    word_rule_assignment_id: uuid.UUID,
    grammar_rule_row_id: uuid.UUID,
    form: str,
    commit: bool = True,
) -> WordForm:
    word_form = WordForm(
        word_rule_assignment_id=word_rule_assignment_id,
        grammar_rule_row_id=grammar_rule_row_id,
        form=form,
    )
    db.add(word_form)
    _commit_or_flush(db, commit)
    db.refresh(word_form)
    return word_form


def get_or_create_word_form(
    db: Session,
    word_rule_assignment_id: uuid.UUID,
    grammar_rule_row_id: uuid.UUID,
    form: str,
    commit: bool = True,
) -> WordForm:
    existing = (
        db.query(WordForm)
        .filter(
            WordForm.word_rule_assignment_id == word_rule_assignment_id,
            WordForm.grammar_rule_row_id == grammar_rule_row_id,
            WordForm.form == form,
        )
        .first()
    )
    if existing is not None:
        return existing
    return create_word_form(db, word_rule_assignment_id, grammar_rule_row_id, form, commit=commit)

# deduplicates on (word_rule_assignment_id, form) only, ignoring grammar_rule_row_id.

def get_or_create_word_form_global(
    db: Session,
    word_rule_assignment_id: uuid.UUID,
    form: str,
    grammar_rule_row_id: uuid.UUID,
    commit: bool = True,
) -> WordForm:
    existing = (
        db.query(WordForm)
        .filter(
            WordForm.word_rule_assignment_id == word_rule_assignment_id,
            WordForm.form == form,
        )
        .first()
    )
    if existing is not None:
        return existing
    return create_word_form(db, word_rule_assignment_id, grammar_rule_row_id, form, commit=commit)


def create_word_form_translation(
    db: Session,
    word_form_id: uuid.UUID,
    language_id: uuid.UUID,
    translation: str,
    commit: bool = True,
) -> WordFormTranslation:
    word_form_translation = WordFormTranslation(
        word_form_id=word_form_id,
        language_id=language_id,
        translation=translation,
    )
    db.add(word_form_translation)
    _commit_or_flush(db, commit)
    db.refresh(word_form_translation)
    return word_form_translation


def get_or_create_word_form_translation(
    db: Session,
    word_form_id: uuid.UUID,
    language_id: uuid.UUID,
    translation: str,
    commit: bool = True,
) -> WordFormTranslation:
    existing = (
        db.query(WordFormTranslation)
        .filter(
            WordFormTranslation.word_form_id == word_form_id,
            WordFormTranslation.language_id == language_id,
        )
        .first()
    )
    if existing is not None:
        return existing
    return create_word_form_translation(db, word_form_id, language_id, translation, commit=commit)


def create_sentence(
    db: Session,
    template: str,
    language_id: uuid.UUID,
    word_category_id: uuid.UUID,
    grammar_rule_id: uuid.UUID,
    row_position: int,
    commit: bool = True,
) -> Sentence:
    sentence = Sentence(
        template=template,
        language_id=language_id,
        word_category_id=word_category_id,
        grammar_rule_id=grammar_rule_id,
        row_position=row_position,
    )
    db.add(sentence)
    _commit_or_flush(db, commit)
    db.refresh(sentence)
    return sentence


def create_sentence_translation(
    db: Session,
    sentence_id: uuid.UUID,
    language_id: uuid.UUID,
    template: str,
    commit: bool = True,
) -> SentenceTranslation:
    sentence_translation = SentenceTranslation(
        sentence_id=sentence_id,
        language_id=language_id,
        template=template,
    )
    db.add(sentence_translation)
    _commit_or_flush(db, commit)
    db.refresh(sentence_translation)
    return sentence_translation


def create_word_form_sentence(
    db: Session,
    word_form_id: uuid.UUID,
    sentence_id: uuid.UUID,
    commit: bool = True,
) -> WordFormSentence:
    word_form_sentence = WordFormSentence(
        word_form_id=word_form_id,
        sentence_id=sentence_id,
    )
    db.add(word_form_sentence)
    _commit_or_flush(db, commit)
    db.refresh(word_form_sentence)
    return word_form_sentence


def count_saved_data(db: Session, grammar_rule_id: uuid.UUID) -> dict[str, int]:
    sentences = (
        db.query(Sentence)
        .filter(Sentence.grammar_rule_id == grammar_rule_id)
        .count()
    )
    word_forms = (
        db.query(WordForm)
        .join(
            WordRuleAssignment,
            WordForm.word_rule_assignment_id == WordRuleAssignment.id,
        )
        .filter(WordRuleAssignment.grammar_rule_id == grammar_rule_id)
        .count()
    )
    base_words = (
        db.query(WordRuleAssignment.base_word_id)
        .filter(WordRuleAssignment.grammar_rule_id == grammar_rule_id)
        .distinct()
        .count()
    )
    return {
        "sentences": sentences,
        "word_forms": word_forms,
        "base_words": base_words,
    }
