import re

from graphs.models import (
    AdjectiveTableLayout,
    NounTableLayout,
    TableData,
    TableRow,
)

COLUMN_ROLES = {
    "verb": {0: "label", 1: "form", 2: "example", 3: "explanation"},
}
DEFAULT_COLUMN_ROLES = {0: "label", 1: "explanation", 2: "example"}

NOUN_COLUMN_COUNT = 8
NOUN_SIDE_COLUMN_COUNT = NOUN_COLUMN_COUNT // 2
NOUN_LAYOUTS = frozenset(layout.value for layout in NounTableLayout)
NOUN_LAYOUT_HEADERS = {
    NounTableLayout.noun_number: ("Singular", "Plural"),
    NounTableLayout.noun_gender: ("Masculine", "Feminine"),
}
# Each noun row holds a pair: columns 0-3 are the first side (singular or
# masculine) and columns 4-7 are the second side (plural or feminine).
NOUN_SIDE_COLUMNS = (
    {"form": 0, "translation": 1, "explanation": 2, "example": 3},
    {"form": 4, "translation": 5, "explanation": 6, "example": 7},
)
# Fragment titles are rendered as "<general title> — <side header>" by
# generate_fragmented_tables_node; the merge below strips the suffix back off.
NOUN_FRAGMENT_TITLE_SEPARATOR = " — "

ADJECTIVE_COLUMN_COUNT = 8
ADJECTIVE_SIDE_COLUMN_COUNT = ADJECTIVE_COLUMN_COUNT // 2
ADJECTIVE_LAYOUTS = frozenset(layout.value for layout in AdjectiveTableLayout)
# The unified flow produces two pair tables from one rule: a number table
# (singular/plural) and a gender table (masculine/feminine). Each side pair is
# identified by the first header of its two 4-column sides.
ADJECTIVE_NUMBER_SIDE_HEADERS = ("Singular", "Plural")
ADJECTIVE_GENDER_SIDE_HEADERS = ("Masculine", "Feminine")
# Each adjective row holds a pair of carrier noun+adjective phrases: columns
# 0-3 are the first side (singular or masculine) and columns 4-7 are the second
# side (plural or feminine).
ADJECTIVE_SIDE_COLUMNS = (
    {"form": 0, "translation": 1, "explanation": 2, "example": 3},
    {"form": 4, "translation": 5, "explanation": 6, "example": 7},
)
ADJECTIVE_FRAGMENT_TITLE_SEPARATOR = " — "

# Other-rules tables (demonstrative, possessive, superlative, ...) are a
# single 4-column table: adjective, translation, explanation, example.
ADJECTIVE_OTHER_COLUMN_COUNT = 4
ADJECTIVE_OTHER_COLUMNS = {
    "form": 0,
    "translation": 1,
    "explanation": 2,
    "example": 3,
}

# Shared shape of every 8-column pair table (noun or adjective): two 4-column
# sides split at these starts, titles joined with the same separator.
PAIR_TABLE_COLUMN_COUNT = 8
PAIR_TABLE_SIDE_COLUMN_COUNT = PAIR_TABLE_COLUMN_COUNT // 2
PAIR_TABLE_SIDE_STARTS = (0, PAIR_TABLE_SIDE_COLUMN_COUNT)
PAIR_FRAGMENT_TITLE_SEPARATOR = " — "


def general_tables_from_table(table: TableData) -> list[dict]:
    """Wrap one generated table in the list-based graph state shape."""
    return [table.model_dump()]


def column_roles(word_category_slug: str) -> dict[int, str]:
    return COLUMN_ROLES.get(word_category_slug, DEFAULT_COLUMN_ROLES)


def role_to_column(roles: dict[int, str]) -> dict[str, int]:
    return {role: index for index, role in roles.items()}


def cell_at_role(cells: list[str], role_lookup: dict[str, int], role: str) -> str | None:
    column = role_lookup.get(role)
    if column is None or column >= len(cells):
        return None
    return cells[column]


def noun_side_cell(cells: list[str], columns: dict[str, int], role: str) -> str:
    index = columns[role]
    if index >= len(cells):
        return ""
    return (cells[index] or "").strip()


def require_noun_layout(layout: str | NounTableLayout | None) -> NounTableLayout:
    """Validate a noun table layout, accepting raw strings and enum members."""
    try:
        return NounTableLayout(layout)
    except ValueError:
        valid = " or ".join(sorted(NOUN_LAYOUTS))
        raise ValueError(
            f"Noun table must set noun_table_layout to {valid}"
        ) from None


def require_adjective_layout(
    layout: str | AdjectiveTableLayout | None,
) -> AdjectiveTableLayout:
    """Validate an adjective table layout, accepting raw strings and members."""
    try:
        return AdjectiveTableLayout(layout)
    except ValueError:
        valid = " or ".join(sorted(ADJECTIVE_LAYOUTS))
        raise ValueError(
            f"Adjective table must set adjective_table_layout to {valid}"
        ) from None


def pair_base_title(title: str) -> str:
    """Strip the " — <side>" fragment suffix back to the general title."""
    return title.split(PAIR_FRAGMENT_TITLE_SEPARATOR, 1)[0]


def is_adjective_other_table(table: dict) -> bool:
    """Whether a table holds other-rule adjectives (one form per row).

    True for the "adj_other" layout, or — when the layout was dropped by an
    edit round-trip — for any 4-column table. Anything else (8-column pair
    tables, odd shapes) is not an other-rule table.
    """
    if table.get("adjective_table_layout") == AdjectiveTableLayout.adj_other:
        return True
    return table.get("adjective_table_layout") is None and len(
        table.get("headers", [])
    ) == ADJECTIVE_OTHER_COLUMN_COUNT


def is_adjective_number_table(table: dict) -> bool:
    """Whether an 8-column pair table is the number (singular/plural) side.

    Detected from the first header: the number prompt mandates the Singular
    concept there ("Singular" is spelled the same in English, Spanish,
    German, and Portuguese). Any other first header — Masculine/Masculino,
    ... — means the gender side, which is also the safe default: both sides
    are stored, so nothing is lost if a language spells it differently.
    """
    headers = table.get("headers", [])
    if len(headers) != ADJECTIVE_COLUMN_COUNT:
        return False
    return headers[0].strip().lower() == "singular"


def is_adjective_pair_table(table: dict) -> bool:
    """Whether a table holds an 8-column adjective pair (number/gender).

    True for any table with the pair shape: a set layout that is not
    "adj_other", or — when the layout was dropped by an edit round-trip —
    any 8-column table. Anything else (other-rule and odd shapes) falls back
    to the generic single-row processing.
    """
    if is_adjective_other_table(table):
        return False
    return table.get("adjective_table_layout") is not None or len(
        table.get("headers", [])
    ) == ADJECTIVE_COLUMN_COUNT


def _dict_row_position(row: dict | TableRow, index: int) -> tuple[int, int]:
    position = (
        row.get("row_position") if isinstance(row, dict) else row.row_position
    )
    return (position if position is not None else index, index)


def _dict_row_cells(row: dict | TableRow) -> list[str]:
    return row.get("cells", []) if isinstance(row, dict) else row.cells


def split_pair_table(
    table: dict, *, layout_field: str, entity_name: str
) -> list[dict]:
    """Split an 8-column pair table into its two 4-column sides.

    The layout value is carried over untouched (it may be None — the split
    never invents one). Fragment titles are "<title> — <side header>".
    """
    headers = table.get("headers", [])
    rows = table.get("rows", [])
    layout = table.get(layout_field)

    if len(headers) != PAIR_TABLE_COLUMN_COUNT:
        raise ValueError(
            f"{entity_name} table must have {PAIR_TABLE_COLUMN_COUNT} columns "
            f"to fragment, got {len(headers)}"
        )
    for row in rows:
        if len(_dict_row_cells(row)) != PAIR_TABLE_COLUMN_COUNT:
            raise ValueError(
                f"Every {entity_name.lower()} table row must have "
                f"{PAIR_TABLE_COLUMN_COUNT} cells to fragment, "
                f"got {len(_dict_row_cells(row))}"
            )

    fragments = []
    for fragment_id, start in enumerate(PAIR_TABLE_SIDE_STARTS, start=1):
        end = start + PAIR_TABLE_SIDE_COLUMN_COUNT
        side_headers = headers[start:end]
        side_title = (
            f"{table['title']}{PAIR_FRAGMENT_TITLE_SEPARATOR}{side_headers[0]}"
            if side_headers
            else table["title"]
        )
        fragment_rows = [
            TableRow(
                cells=_dict_row_cells(row)[start:end],
                row_position=row.get("row_position"),
            )
            for row in rows
        ]
        fragments.append(
            TableData(
                title=side_title,
                headers=side_headers,
                rows=fragment_rows,
                fragmented_table_id=fragment_id,
                **{layout_field: layout},
            ).model_dump()
        )

    return fragments


def merge_pair_sides(
    first_side: dict,
    second_side: dict,
    general: dict | None,
    *,
    layout_field: str,
    pair_error: str,
) -> TableData:
    """Zip two 4-column side fragments back into one 8-column pair table."""
    first_side_rows = sorted(
        enumerate(first_side.get("rows", [])),
        key=lambda item: _dict_row_position(item[1], item[0]),
    )
    second_side_rows = sorted(
        enumerate(second_side.get("rows", [])),
        key=lambda item: _dict_row_position(item[1], item[0]),
    )
    if len(first_side_rows) != len(second_side_rows):
        raise ValueError(pair_error)

    rows = []
    for (first_side_index, first_side_row), (_, second_side_row) in zip(first_side_rows, second_side_rows):
        first_side_cells = _dict_row_cells(first_side_row)
        second_side_cells = _dict_row_cells(second_side_row)
        first_side_position = (
            first_side_row.get("row_position")
            if isinstance(first_side_row, dict)
            else first_side_row.row_position
        )
        rows.append(
            TableRow(
                cells=[*first_side_cells, *second_side_cells],
                row_position=(
                    first_side_position if first_side_position is not None else first_side_index
                ),
            )
        )

    layout = (
        first_side.get(layout_field)
        or second_side.get(layout_field)
        or (general.get(layout_field) if general else None)
    )
    title = general["title"] if general is not None else first_side["title"]
    if general is None and PAIR_FRAGMENT_TITLE_SEPARATOR in title:
        title = pair_base_title(title)

    return TableData(
        title=title,
        headers=[*first_side.get("headers", []), *second_side.get("headers", [])],
        rows=rows,
        **{layout_field: layout},
    )


def select_pair_tables(
    tables: list[TableData],
    *,
    layout_field: str,
    entity_name: str,
) -> list[TableData]:
    """Pick the savable tables: merged pairs when fragments exist.

    Fragments are grouped by base title (the general title without the
    " — <side>" suffix); each group must hold exactly one pair of 4-column
    sides. Groups merge in fragment-id order so the number pair comes before
    the gender pair. Without fragments, the general tables pass through.
    """
    fragments = [
        table for table in tables if table.fragmented_table_id is not None
    ]
    if not fragments:
        return [table for table in tables if table.fragmented_table_id is None]

    generals = [
        table
        for table in tables
        if table.fragmented_table_id is None
        and len(table.headers) == PAIR_TABLE_COLUMN_COUNT
    ]
    groups: dict[str, list[TableData]] = {}
    for table in fragments:
        groups.setdefault(pair_base_title(table.title), []).append(table)

    merged = []
    ordered_bases = sorted(
        groups,
        key=lambda base: min(t.fragmented_table_id or 0 for t in groups[base]),
    )
    for base in ordered_bases:
        group = sorted(
            groups[base], key=lambda t: t.fragmented_table_id or 0
        )
        if len(group) != 2 or any(
            len(t.headers) != PAIR_TABLE_SIDE_COLUMN_COUNT for t in group
        ):
            raise ValueError(
                f"{entity_name} fragmented tables for '{base}' must form "
                "exactly one pair of 4-column sides. Regenerate the table "
                "before saving."
            )
        general = next(
            (g for g in generals if pair_base_title(g.title) == base), None
        )
        merged.append(
            merge_pair_sides(
                group[0].model_dump(),
                group[1].model_dump(),
                general.model_dump() if general else None,
                layout_field=layout_field,
                pair_error=(
                    f"{entity_name} side tables for '{base}' must contain the "
                    "same number of pairs. Regenerate the table before saving."
                ),
            )
        )
    return merged


def select_adjective_tables(tables: list[TableData]) -> list[TableData]:
    """Merge adjective side fragments back into their 8-column pair tables."""
    return select_pair_tables(
        tables, layout_field="adjective_table_layout", entity_name="Adjective"
    )


def tokenize_words(text: str) -> list[str]:
    return [word for word in re.findall(r"[\w']+", text)]


def _row_order_key(row: TableRow, index: int) -> tuple[int, int]:
    return (row.row_position if row.row_position is not None else index, index)


def merge_noun_side_fragments(
    fragments: list[TableData],
    general_table: TableData | None,
) -> list[TableData]:
    """Combine the two 4-column side fragments into one 8-column pair table."""
    if len(fragments) != 2 or any(
        len(fragment.headers) != NOUN_SIDE_COLUMN_COUNT for fragment in fragments
    ):
        return fragments

    first_side, second_side = sorted(fragments, key=lambda table: table.fragmented_table_id or 0)
    first_side_rows = sorted(
        enumerate(first_side.rows), key=lambda item: _row_order_key(item[1], item[0])
    )
    second_side_rows = sorted(
        enumerate(second_side.rows), key=lambda item: _row_order_key(item[1], item[0])
    )
    if len(first_side_rows) != len(second_side_rows):
        raise ValueError(
            "Noun side tables must contain the same number of pairs. "
            "Regenerate the table before saving."
        )

    rows = []
    for (first_side_index, first_side_row), (_, second_side_row) in zip(first_side_rows, second_side_rows):
        rows.append(
            TableRow(
                cells=[*first_side_row.cells, *second_side_row.cells],
                row_position=(
                    first_side_row.row_position
                    if first_side_row.row_position is not None
                    else first_side_index
                ),
            )
        )

    layout = (
        first_side.noun_table_layout
        or second_side.noun_table_layout
        or (general_table.noun_table_layout if general_table else None)
    )
    title = general_table.title if general_table is not None else first_side.title
    if general_table is None and NOUN_FRAGMENT_TITLE_SEPARATOR in title:
        title = title.split(NOUN_FRAGMENT_TITLE_SEPARATOR, 1)[0]

    return [
        TableData(
            title=title,
            headers=[*first_side.headers, *second_side.headers],
            rows=rows,
            noun_table_layout=layout,
        )
    ]


def select_noun_tables(tables: list[TableData]) -> list[TableData]:
    fragments = [
        table for table in tables if table.fragmented_table_id is not None
    ]
    general = next(
        (
            table
            for table in tables
            if table.fragmented_table_id is None
            and len(table.headers) == NOUN_COLUMN_COUNT
        ),
        None,
    )
    if fragments:
        return merge_noun_side_fragments(fragments, general)

    return [table for table in tables if table.fragmented_table_id is None]
