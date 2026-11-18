from graphs.models import AdjectiveTableLayout, TableData
from graphs.table_utils import (
    ADJECTIVE_COLUMN_COUNT,
    ADJECTIVE_OTHER_COLUMN_COUNT,
    NOUN_COLUMN_COUNT,
    require_adjective_layout,
    require_noun_layout,
)


def validate_noun_table(table: TableData) -> None:
    require_noun_layout(table.noun_table_layout)
    if len(table.headers) != NOUN_COLUMN_COUNT:
        raise ValueError(
            f"Noun table must have {NOUN_COLUMN_COUNT} columns, "
            f"got {len(table.headers)}"
        )
    for row in table.rows:
        if len(row.cells) != NOUN_COLUMN_COUNT:
            raise ValueError(
                f"Every noun table row must have {NOUN_COLUMN_COUNT} cells, "
                f"got {len(row.cells)}"
            )


def validate_adjective_layout(table: TableData) -> None:
    require_adjective_layout(table.adjective_table_layout)


def validate_adjective_pair_table(table: TableData) -> None:
    """Validate an adjective pair table: a known layout and 8 columns/cells."""
    require_adjective_layout(table.adjective_table_layout)
    if len(table.headers) != ADJECTIVE_COLUMN_COUNT:
        raise ValueError(
            f"Adjective table must have {ADJECTIVE_COLUMN_COUNT} columns, "
            f"got {len(table.headers)}"
        )
    for row in table.rows:
        if len(row.cells) != ADJECTIVE_COLUMN_COUNT:
            raise ValueError(
                f"Every adjective table row must have {ADJECTIVE_COLUMN_COUNT} "
                f"cells, got {len(row.cells)}"
            )


def validate_adjective_other_table(table: TableData) -> None:
    """Validate an other-rules table: the adj_other layout and 4x4 shape."""
    require_adjective_layout(table.adjective_table_layout)
    if table.adjective_table_layout != AdjectiveTableLayout.adj_other:
        raise ValueError(
            "Other-rule adjective tables must set adjective_table_layout to "
            f'"{AdjectiveTableLayout.adj_other.value}", got '
            f'"{table.adjective_table_layout}"'
        )
    if len(table.headers) != ADJECTIVE_OTHER_COLUMN_COUNT:
        raise ValueError(
            f"Adjective other table must have {ADJECTIVE_OTHER_COLUMN_COUNT} "
            f"columns, got {len(table.headers)}"
        )
    for row in table.rows:
        if len(row.cells) != ADJECTIVE_OTHER_COLUMN_COUNT:
            raise ValueError(
                "Every adjective other table row must have "
                f"{ADJECTIVE_OTHER_COLUMN_COUNT} cells, got {len(row.cells)}"
            )
