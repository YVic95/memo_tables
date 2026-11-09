import pytest

from graphs.models import TableData
from graphs.table_utils import (
    ADJECTIVE_COLUMN_COUNT,
    COLUMN_ROLES,
    DEFAULT_COLUMN_ROLES,
    column_roles,
    extract_italic_markers,
    merge_pair_sides,
    pair_base_title,
    require_adjective_layout,
    select_adjective_tables,
    split_pair_table,
)
from tests.graphs.generation_helpers import (
    ADJ_GENDER_HEADERS,
    ADJ_GENDER_TABLE,
    ADJ_NUMBER_HEADERS,
    ADJ_NUMBER_TABLE,
)

VERB_ROLES = {0: "label", 1: "form", 2: "example", 3: "explanation"}


class TestColumnRoles:
    def test_noun_no_longer_has_a_three_column_mapping(self):
        assert "noun" not in COLUMN_ROLES

    def test_verb_roles_are_unchanged(self):
        assert column_roles("verb") == VERB_ROLES

    def test_unsupported_categories_fall_back_to_default(self):
        for slug in ("noun", "adjective", "adverb", "pronoun", "unknown"):
            assert column_roles(slug) == DEFAULT_COLUMN_ROLES


class TestRequireAdjectiveLayout:
    def test_accepts_all_adjective_layouts(self):
        for layout in ("adj_number_gender", "adj_agreement", "adj_other"):
            assert require_adjective_layout(layout).value == layout

    def test_rejects_noun_layouts_and_missing_values(self):
        for layout in ("noun_number", None, "adj_case"):
            with pytest.raises(ValueError, match="adjective_table_layout"):
                require_adjective_layout(layout)


class TestExtractItalicMarkers:
    def test_extracts_adjectives_from_a_bold_carrier_phrase(self):
        assert extract_italic_markers("**el libro *rojo* / los libros *rojos***") == [
            "rojo",
            "rojos",
        ]

    def test_plain_cells_yield_no_markers(self):
        assert extract_italic_markers("el libro") == []
        assert extract_italic_markers("") == []

    def test_bold_without_italics_yields_no_markers(self):
        assert extract_italic_markers("**el libro rojo**") == []


class TestSplitPairTable:
    def test_adjective_number_table_splits_with_layout_preserved(self):
        fragments = split_pair_table(
            ADJ_NUMBER_TABLE.model_dump(),
            layout_field="adjective_table_layout",
            entity_name="Adjective",
        )

        singular, plural = fragments
        assert singular["title"] == f"{ADJ_NUMBER_TABLE.title} — Singular"
        assert plural["title"] == f"{ADJ_NUMBER_TABLE.title} — Plural"
        assert singular["headers"] == ADJ_NUMBER_HEADERS[:4]
        assert plural["headers"] == ADJ_NUMBER_HEADERS[4:]
        assert [f["fragmented_table_id"] for f in (singular, plural)] == [1, 2]
        assert [f["adjective_table_layout"] for f in (singular, plural)] == [
            "adj_number_gender",
            "adj_number_gender",
        ]
        assert [row["cells"] for row in singular["rows"]] == [
            row.cells[:4] for row in ADJ_NUMBER_TABLE.rows
        ]
        assert [row["cells"] for row in plural["rows"]] == [
            row.cells[4:] for row in ADJ_NUMBER_TABLE.rows
        ]

    def test_wrong_column_count_is_rejected_with_entity_name(self):
        table = ADJ_NUMBER_TABLE.model_copy(
            update={"headers": ADJ_NUMBER_HEADERS[:7]}
        )

        with pytest.raises(ValueError, match="Adjective table must have 8 columns"):
            split_pair_table(
                table.model_dump(),
                layout_field="adjective_table_layout",
                entity_name="Adjective",
            )

    def test_pair_base_title_strips_the_side_suffix(self):
        assert pair_base_title("El número — Singular") == "El número"
        assert pair_base_title("Sin sufijo") == "Sin sufijo"


class TestSelectAdjectiveTables:
    def _four_fragments(self):
        number, gender = ADJ_NUMBER_TABLE, ADJ_GENDER_TABLE
        fragments = [
            *split_pair_table(
                number.model_dump(),
                layout_field="adjective_table_layout",
                entity_name="Adjective",
            ),
            *split_pair_table(
                gender.model_dump(),
                layout_field="adjective_table_layout",
                entity_name="Adjective",
            ),
        ]
        for index, fragment in enumerate(fragments[2:], start=3):
            fragment["fragmented_table_id"] = index
        return [
            TableData(**{**f, "adjective_table_layout": f["adjective_table_layout"]})
            for f in fragments
        ]

    def test_two_generals_and_four_fragments_merge_back_losslessly(self):
        tables = [
            ADJ_NUMBER_TABLE,
            ADJ_GENDER_TABLE,
            *self._four_fragments(),
        ]

        merged = select_adjective_tables(tables)

        assert len(merged) == 2
        assert merged[0].title == ADJ_NUMBER_TABLE.title
        assert merged[1].title == ADJ_GENDER_TABLE.title
        assert [row.cells for row in merged[0].rows] == [
            row.cells for row in ADJ_NUMBER_TABLE.rows
        ]
        assert [row.cells for row in merged[1].rows] == [
            row.cells for row in ADJ_GENDER_TABLE.rows
        ]
        assert merged[0].adjective_table_layout == "adj_number_gender"
        assert merged[1].adjective_table_layout == "adj_number_gender"

    def test_fragments_without_generals_merge_under_base_titles(self):
        merged = select_adjective_tables(self._four_fragments())

        assert [t.title for t in merged] == [
            ADJ_NUMBER_TABLE.title,
            ADJ_GENDER_TABLE.title,
        ]

    def test_generals_pass_through_when_nothing_fragmented(self):
        result = select_adjective_tables([ADJ_NUMBER_TABLE, ADJ_GENDER_TABLE])

        assert result == [ADJ_NUMBER_TABLE, ADJ_GENDER_TABLE]

    def test_orphan_fragment_is_rejected(self):
        fragments = self._four_fragments()[:3]

        with pytest.raises(ValueError, match="exactly one pair"):
            select_adjective_tables(fragments)

    def test_row_count_mismatch_is_rejected(self):
        fragments = self._four_fragments()
        fragments[1] = fragments[1].model_copy(update={"rows": []})

        with pytest.raises(ValueError, match="same number of pairs"):
            select_adjective_tables([ADJ_NUMBER_TABLE, *fragments])

    def test_merge_pair_sides_keeps_row_positions(self):
        left = {
            "title": "T — Singular",
            "headers": ADJ_NUMBER_HEADERS[:4],
            "rows": [
                {"cells": ["a", "b", "c", "d"], "row_position": 5},
            ],
            "fragmented_table_id": 1,
            "adjective_table_layout": "adj_number_gender",
        }
        right = {
            "title": "T — Plural",
            "headers": ADJ_NUMBER_HEADERS[4:],
            "rows": [
                {"cells": ["e", "f", "g", "h"], "row_position": 5},
            ],
            "fragmented_table_id": 2,
            "adjective_table_layout": "adj_number_gender",
        }

        merged = merge_pair_sides(
            left, right, None,
            layout_field="adjective_table_layout",
            pair_error="mismatch",
        )

        assert merged.rows[0].cells == ["a", "b", "c", "d", "e", "f", "g", "h"]
        assert merged.rows[0].row_position == 5
        assert merged.title == "T"
        assert ADJECTIVE_COLUMN_COUNT == 8
