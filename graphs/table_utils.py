import re

from graphs.models import NounTableLayout, TableData, TableRow

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
# Each noun row holds a pair: columns 0-3 are the left side (singular or
# masculine) and columns 4-7 are the right side (plural or feminine).
NOUN_SIDE_COLUMNS = (
    {"form": 0, "translation": 1, "explanation": 2, "example": 3},
    {"form": 4, "translation": 5, "explanation": 6, "example": 7},
)
# Fragment titles are rendered as "<general title> — <side header>" by
# generate_fragmented_tables_node; the merge below strips the suffix back off.
NOUN_FRAGMENT_TITLE_SEPARATOR = " — "


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

    left, right = sorted(fragments, key=lambda table: table.fragmented_table_id or 0)
    left_rows = sorted(
        enumerate(left.rows), key=lambda item: _row_order_key(item[1], item[0])
    )
    right_rows = sorted(
        enumerate(right.rows), key=lambda item: _row_order_key(item[1], item[0])
    )
    if len(left_rows) != len(right_rows):
        raise ValueError(
            "Noun side tables must contain the same number of pairs. "
            "Regenerate the table before saving."
        )

    rows = []
    for (left_index, left_row), (_, right_row) in zip(left_rows, right_rows):
        rows.append(
            TableRow(
                cells=[*left_row.cells, *right_row.cells],
                row_position=(
                    left_row.row_position
                    if left_row.row_position is not None
                    else left_index
                ),
            )
        )

    layout = (
        left.noun_table_layout
        or right.noun_table_layout
        or (general_table.noun_table_layout if general_table else None)
    )
    title = general_table.title if general_table is not None else left.title
    if general_table is None and NOUN_FRAGMENT_TITLE_SEPARATOR in title:
        title = title.split(NOUN_FRAGMENT_TITLE_SEPARATOR, 1)[0]

    return [
        TableData(
            title=title,
            headers=[*left.headers, *right.headers],
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
