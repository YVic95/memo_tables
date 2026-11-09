from fastapi import APIRouter, Depends, HTTPException
import uuid
from typing import Annotated
from sqlalchemy.orm import Session
from database import get_db
from crud.language_pairs import get_language_pair_by_id
from crud.rules import get_grammar_rule_by_id, get_word_category_by_id
from crud.table_data import (
    build_adjective_skeleton_tables,
    build_markdown_tables,
    build_noun_skeleton_tables,
    count_saved_data,
    get_table_data,
)
from graphs.models import SaveTablesRequest, TableData
from graphs.table_utils import (
    ADJECTIVE_COLUMN_COUNT,
    ADJECTIVE_LAYOUTS,
    ADJECTIVE_OTHER_COLUMN_COUNT,
    NOUN_COLUMN_COUNT,
    NOUN_LAYOUTS,
    select_adjective_tables,
    select_noun_tables,
)
from models.grammar_rules import GrammarRule
from graphs.save_table_graph import graph

router = APIRouter(tags=["save-tables"])


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'s' if n != 1 else ''}"


def _category_slug(db: Session, rule: GrammarRule) -> str | None:
    try:
        category_id = uuid.UUID(str(rule.word_category_id))
    except (ValueError, AttributeError, TypeError):
        # Test doubles and stale payloads can carry a non-UUID category id.
        return None
    category = get_word_category_by_id(db, category_id)
    return category.slug if category else None


def _validate_tables(
    tables: list[TableData],
    word_category_slug: str | None = None,
) -> None:
    if not tables:
        raise HTTPException(status_code=400, detail="Tables list must not be empty")

    is_noun = word_category_slug == "noun"
    is_adjective = word_category_slug == "adjective"
    for table in tables:
        if not table.rows:
            raise HTTPException(status_code=400, detail=f"Table '{table.title}' must have at least one row")

        if is_noun and table.noun_table_layout not in NOUN_LAYOUTS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Noun table '{table.title}' is missing its table layout. "
                    "Regenerate the table before saving."
                ),
            )
        if is_noun and len(table.headers) != NOUN_COLUMN_COUNT:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Noun table '{table.title}' must have exactly "
                    f"{NOUN_COLUMN_COUNT} columns, got {len(table.headers)}. "
                    "Regenerate the table before saving."
                ),
            )
        if is_adjective:
            layout = table.adjective_table_layout
            headers = len(table.headers)
            if layout is None:
                if headers not in (ADJECTIVE_COLUMN_COUNT, ADJECTIVE_OTHER_COLUMN_COUNT):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Adjective table '{table.title}' is missing its table "
                            f"layout and must have {ADJECTIVE_COLUMN_COUNT} columns "
                            f"(pair tables) or {ADJECTIVE_OTHER_COLUMN_COUNT} columns "
                            f"(other-rule tables), got {headers}. "
                            "Regenerate the table before saving."
                        ),
                    )
            elif layout == "adj_other":
                if headers != ADJECTIVE_OTHER_COLUMN_COUNT:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Adjective table '{table.title}' must have exactly "
                            f"{ADJECTIVE_OTHER_COLUMN_COUNT} columns, got {headers}. "
                            "Regenerate the table before saving."
                        ),
                    )
            else:
                if layout not in ADJECTIVE_LAYOUTS:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Adjective table '{table.title}' is missing its table "
                            "layout. Regenerate the table before saving."
                        ),
                    )
                if headers != ADJECTIVE_COLUMN_COUNT:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Adjective table '{table.title}' must have exactly "
                            f"{ADJECTIVE_COLUMN_COUNT} columns, got {headers}. "
                            "Regenerate the table before saving."
                        ),
                    )

        for i, row in enumerate(table.rows):
            if len(row.cells) != len(table.headers):
                raise HTTPException(
                    status_code=400,
                    detail=f"Row {i + 1} in table '{table.title}' has {len(row.cells)} cells but headers have {len(table.headers)} columns",
                )


@router.post("/api/save-tables")
def save_tables(
    body: SaveTablesRequest,
    db: Annotated[Session, Depends(get_db)],
):
    pair = get_language_pair_by_id(db, body.language_pair_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="Language pair not found")

    rule = get_grammar_rule_by_id(db, body.grammar_rule_id)
    if rule is None:
        raise HTTPException(status_code=400, detail="Grammar rule not found")

    word_category_slug = _category_slug(db, rule)

    if word_category_slug == "noun":
        try:
            tables_to_save = select_noun_tables(body.tables)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    elif word_category_slug == "adjective":
        try:
            tables_to_save = select_adjective_tables(body.tables)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    else:
        fragmented = [table for table in body.tables if table.fragmented_table_id is not None]
        tables_to_save = fragmented if fragmented else [table for table in body.tables if table.fragmented_table_id is None]

    _validate_tables(tables_to_save, word_category_slug)

    try:
        graph.invoke(
            {
                "db": db,
                "language_pair_id": body.language_pair_id,
                "session_id": str(body.session_id),
                "grammar_rule_id": body.grammar_rule_id,
                "tables": [table.model_dump() for table in tables_to_save],
                "target_language_id": None,
                "native_language_id": None,
                "word_category_slug": None,
                "base_words_to_save": [],
                "base_word_translations": {},
                "form_to_base_word_id": {},
            }
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    tables_desc = ", ".join(
        f"'{table.title}' ({_plural(len(table.rows), 'row')})" for table in tables_to_save
    )
    counts = count_saved_data(db, body.grammar_rule_id)
    message = (
        f"Saved {_plural(len(tables_to_save), 'table')}: {tables_desc}. "
        f"Stored {_plural(counts['sentences'], 'sentence')}, "
        f"{_plural(counts['word_forms'], 'word form')}, "
        f"{_plural(counts['base_words'], 'base word')}."
    )

    titles_by_no = {table.fragmented_table_id or 0: table.title for table in tables_to_save}
    noun_layout = next(
        (
            table.noun_table_layout
            for table in tables_to_save
            if table.noun_table_layout is not None
        ),
        None,
    )
    skeleton_table, skeleton_titles = _build_skeleton_summary(
        db, rule, titles_by_no, word_category_slug, noun_layout,
        tables_to_save=tables_to_save,
    )

    return {
        "status": "saved",
        "grammar_rule_id": str(body.grammar_rule_id),
        "rule_title": rule.name,
        "message": message,
        "skeleton_table": skeleton_table,
        "skeleton_titles": skeleton_titles,
    }


def _build_skeleton_summary(
    db: Session,
    rule: GrammarRule,
    titles_by_no: dict[int, str],
    word_category_slug: str | None = None,
    noun_layout: str | None = None,
    tables_to_save: list[TableData] | None = None,
) -> tuple[dict[str, str], dict[str, list[str]]]:
    slug = word_category_slug or _category_slug(db, rule) or "table"

    if slug == "noun" and noun_layout:
        titles = [titles_by_no.get(table_no, rule.name) for table_no in sorted(titles_by_no)]
        return build_noun_skeleton_tables(db, rule.id, noun_layout), {slug: titles}

    if slug == "adjective" and tables_to_save:
        # table_no matches the persistence order: the fragment id when set,
        # otherwise the table's index — the same rule process_all_tables_node
        # uses, so skeleton groups line up with the stored positions.
        headers_by_no: dict[int, tuple[str, ...]] = {}
        titles: list[str] = []
        for index, table in enumerate(tables_to_save):
            table_no = (
                table.fragmented_table_id
                if table.fragmented_table_id is not None
                else index
            )
            if len(table.headers) == ADJECTIVE_OTHER_COLUMN_COUNT:
                headers_by_no[table_no] = (table.headers[0],)
            else:
                headers_by_no[table_no] = (
                    table.headers[0],
                    table.headers[len(table.headers) // 2],
                )
            titles.append(table.title)
        return build_adjective_skeleton_tables(db, rule.id, headers_by_no), {slug: titles}

    table_data = get_table_data(db, rule.id, rule.word_category_id)
    if not table_data:
        return {slug: ""}, {slug: []}

    titles = [titles_by_no.get(group["table_no"], rule.name) for group in table_data]
    return build_markdown_tables(table_data, slug), {slug: titles}
