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
from graphs.models import NounTableLayout
from graphs.table_utils import NOUN_LAYOUT_HEADERS, NOUN_SIDE_COLUMNS


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


def get_table_data(
    db: Session,
    grammar_rule_id: uuid.UUID,
    word_category_id: uuid.UUID | None = None,
) -> list[dict]:
    rows = (
        db.query(GrammarRuleRow)
        .filter(GrammarRuleRow.grammar_rule_id == grammar_rule_id)
        .order_by(GrammarRuleRow.table_no, GrammarRuleRow.position)
        .all()
    )

    if not rows:
        return []

    assignments_query = (
        db.query(WordRuleAssignment, BaseWord)
        .join(BaseWord, WordRuleAssignment.base_word_id == BaseWord.id)
        .filter(WordRuleAssignment.grammar_rule_id == grammar_rule_id)
    )
    if word_category_id is not None:
        assignments_query = assignments_query.filter(
            BaseWord.word_category_id == word_category_id
        )
    assignments = assignments_query.all()

    forms = (
        db.query(WordForm)
        .join(
            WordRuleAssignment,
            WordForm.word_rule_assignment_id == WordRuleAssignment.id,
        )
        .filter(WordRuleAssignment.grammar_rule_id == grammar_rule_id)
        .all()
    )

    form_map: dict[tuple[uuid.UUID, uuid.UUID], str] = {}
    for word_form in forms:
        form_map[(word_form.word_rule_assignment_id, word_form.grammar_rule_row_id)] = word_form.form

    grouped: dict[int, list[dict]] = {}
    for row in rows:
        table_no = row.table_no
        if table_no not in grouped:
            grouped[table_no] = []
        for assignment, base_word in assignments:
            form = form_map.get((assignment.id, row.id))
            grouped[table_no].append({
                "label": row.label,
                "base_word_text": base_word.text,
                "form": form,
            })

    return [
        {"table_no": table_no, "entries": entries}
        for table_no, entries in sorted(grouped.items())
    ]


def _format_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    def pad_row(cells: list[str]) -> str:
        padded = [cells[i].ljust(col_widths[i]) for i in range(len(cells))]
        return "| " + " | ".join(padded) + " |"

    header_line = pad_row(headers)
    separator_line = "| " + " | ".join("-" * w for w in col_widths) + " |"
    data_lines = [pad_row(row) for row in rows]

    return "\n".join([header_line, separator_line] + data_lines)


def _build_single_table(entries: list[dict], word_category_slug: str) -> str:
    category_prefix = word_category_slug.replace("_", " ").title()

    label_to_base_words: dict[str, dict[str, str | None]] = {}
    ordered_labels: list[str] = []
    for entry in entries:
        label = entry["label"]
        if label not in label_to_base_words:
            label_to_base_words[label] = {}
            ordered_labels.append(label)
        label_to_base_words[label][entry["base_word_text"]] = entry["form"]

    base_words = list(dict.fromkeys(
        entry["base_word_text"] for entry in entries
    ))

    headers = ["Label"] + [f"{category_prefix}: {word}" for word in base_words]
    all_rows: list[list[str]] = []
    for label in ordered_labels:
        cells = [label]
        for word in base_words:
            form = label_to_base_words[label].get(word)
            cells.append(form if form is not None else "")
        all_rows.append(cells)

    return _format_markdown_table(headers, all_rows)


def build_markdown_tables(
    table_data: list[dict],
    word_category_slug: str,
) -> dict[str, str]:
    if not table_data:
        return {word_category_slug: ""}

    tables = [
        _build_single_table(group["entries"], word_category_slug)
        for group in table_data
    ]

    return {word_category_slug: "\n\n".join(tables)}


def build_noun_skeleton_tables(
    db: Session,
    grammar_rule_id: uuid.UUID,
    noun_layout: str,
) -> dict[str, str]:
    """Render the two-column skeleton for a saved noun rule.

    Two grammar_rule_rows are persisted per pair, at positions
    ``pair_index * (number of sides)`` through ``pair_index * (number of
    sides) + 1``. They are grouped back into a single skeleton row under the
    layout's two side headers.
    """
    try:
        layout = NounTableLayout(noun_layout)
    except ValueError:
        return {"noun": ""}
    headers = NOUN_LAYOUT_HEADERS[layout]
    side_count = len(NOUN_SIDE_COLUMNS)

    rows = (
        db.query(GrammarRuleRow)
        .filter(GrammarRuleRow.grammar_rule_id == grammar_rule_id)
        .order_by(GrammarRuleRow.table_no, GrammarRuleRow.position)
        .all()
    )
    if not rows:
        return {"noun": ""}

    grouped: dict[int, dict[int, dict[int, str]]] = {}
    for row in rows:
        pair_index, side_index = divmod(row.position, side_count)
        grouped.setdefault(row.table_no, {}).setdefault(pair_index, {})[side_index] = row.label

    tables = []
    for table_no in sorted(grouped):
        table_rows = [
            [pair.get(0, ""), pair.get(1, "")]
            for _, pair in sorted(grouped[table_no].items())
        ]
        tables.append(_format_markdown_table(list(headers), table_rows))

    return {"noun": "\n\n".join(tables)}


def build_adjective_skeleton_tables(
    db: Session,
    grammar_rule_id: uuid.UUID,
    headers_by_table_no: dict[int, tuple[str, str]],
) -> dict[str, str]:
    """Render the skeleton tables for a saved adjective rule.

    The unified flow persists one pair table per table_no (0 for number, 1
    for gender): two grammar_rule_rows per pair at positions
    ``pair_index * 2`` and ``pair_index * 2 + 1``. Each group renders under
    its mapped side headers. Groups without a header mapping (e.g. stale rows
    from an earlier save) are skipped rather than rendered under wrong
    headers.
    """
    rows = (
        db.query(GrammarRuleRow)
        .filter(GrammarRuleRow.grammar_rule_id == grammar_rule_id)
        .order_by(GrammarRuleRow.table_no, GrammarRuleRow.position)
        .all()
    )
    if not rows:
        return {"adjective": ""}

    grouped: dict[int, dict[int, dict[int, str]]] = {}
    for row in rows:
        pair_index, side_index = divmod(row.position, 2)
        grouped.setdefault(row.table_no, {}).setdefault(pair_index, {})[side_index] = row.label

    tables = []
    for table_no in sorted(grouped):
        headers = headers_by_table_no.get(table_no)
        if headers is None:
            continue
        table_rows = [
            [pair.get(0, ""), pair.get(1, "")]
            for _, pair in sorted(grouped[table_no].items())
        ]
        tables.append(_format_markdown_table(list(headers), table_rows))

    return {"adjective": "\n\n".join(tables)}
