import json

import pytest

import graphs.nodes.generate_fragmented_tables_node as node_module
from graphs.models import FragmentationOutput, TableData, TableRow
from graphs.nodes.generate_fragmented_tables_node import generate_fragmented_tables_node
from tests.graphs.generation_helpers import (
    ADJ_AGREEMENT_TABLE,
    ADJ_GENDER_TABLE,
    ADJ_NUMBER_HEADERS,
    ADJ_NUMBER_TABLE,
    NOUN_GENDER_HEADERS,
    NOUN_GENDER_TABLE,
    NOUN_NUMBER_HEADERS,
    NOUN_NUMBER_TABLE,
)


def _noun_state(table: TableData) -> dict:
    return {
        "word_category_slug": "noun",
        "general_tables": [table.model_dump()],
    }


def _adjective_state() -> dict:
    return {
        "word_category_slug": "adjective",
        "general_tables": [
            ADJ_NUMBER_TABLE.model_dump(),
            ADJ_GENDER_TABLE.model_dump(),
        ],
    }


class _ExplodingChain:
    def invoke(self, *args, **kwargs):
        raise AssertionError("noun fragmentation must not call the LLM")


def test_number_table_splits_into_singular_and_plural_fragments(monkeypatch):
    monkeypatch.setattr(node_module, "fragmentation_chain", _ExplodingChain())

    result = generate_fragmented_tables_node(_noun_state(NOUN_NUMBER_TABLE))

    assert result["should_fragment"] is True
    singular, plural = result["fragmented_tables"]

    assert singular["title"] == f"{NOUN_NUMBER_TABLE.title} — Singular"
    assert plural["title"] == f"{NOUN_NUMBER_TABLE.title} — Plural"
    assert singular["headers"] == NOUN_NUMBER_HEADERS[:4]
    assert plural["headers"] == NOUN_NUMBER_HEADERS[4:]
    assert [f["fragmented_table_id"] for f in (singular, plural)] == [1, 2]
    assert [f["noun_table_layout"] for f in (singular, plural)] == [
        "noun_number",
        "noun_number",
    ]

    for fragment in (singular, plural):
        assert all(len(row["cells"]) == 4 for row in fragment["rows"])

    assert [row["cells"] for row in singular["rows"]] == [
        row.cells[:4] for row in NOUN_NUMBER_TABLE.rows
    ]
    assert [row["cells"] for row in plural["rows"]] == [
        row.cells[4:] for row in NOUN_NUMBER_TABLE.rows
    ]


def test_gender_table_splits_into_masculine_and_feminine_fragments(monkeypatch):
    monkeypatch.setattr(node_module, "fragmentation_chain", _ExplodingChain())

    result = generate_fragmented_tables_node(_noun_state(NOUN_GENDER_TABLE))

    masculine, feminine = result["fragmented_tables"]

    assert masculine["title"] == f"{NOUN_GENDER_TABLE.title} — Masculino"
    assert feminine["title"] == f"{NOUN_GENDER_TABLE.title} — Femenino"
    assert masculine["headers"] == NOUN_GENDER_HEADERS[:4]
    assert feminine["headers"] == NOUN_GENDER_HEADERS[4:]
    assert [f["noun_table_layout"] for f in (masculine, feminine)] == [
        "noun_gender",
        "noun_gender",
    ]
    assert [row["cells"] for row in masculine["rows"]] == [
        row.cells[:4] for row in NOUN_GENDER_TABLE.rows
    ]
    assert [row["cells"] for row in feminine["rows"]] == [
        row.cells[4:] for row in NOUN_GENDER_TABLE.rows
    ]


def test_single_pair_noun_table_still_splits_into_two_one_row_fragments():
    table = TableData(
        title="El número del sustantivo",
        headers=NOUN_NUMBER_HEADERS,
        rows=[
            TableRow(
                cells=[
                    "la mesa",
                    "the table",
                    "Feminine; singular article 'la'",
                    "La mesa es grande.",
                    "las mesas",
                    "the tables",
                    "Plural adds -s",
                    "Las mesas son grandes.",
                ],
                row_position=0,
            )
        ],
        noun_table_layout="noun_number",
    )

    result = generate_fragmented_tables_node(_noun_state(table))

    singular, plural = result["fragmented_tables"]
    assert len(singular["rows"]) == 1
    assert len(plural["rows"]) == 1
    assert singular["rows"][0]["cells"] == table.rows[0].cells[:4]
    assert plural["rows"][0]["cells"] == table.rows[0].cells[4:]
    assert len(singular["rows"][0]["cells"]) == 4
    assert len(plural["rows"][0]["cells"]) == 4


def test_each_fragment_row_matches_its_general_table_pair_and_position():
    table = TableData(
        title="El género del sustantivo",
        headers=NOUN_GENDER_HEADERS,
        rows=[
            TableRow(cells=NOUN_GENDER_TABLE.rows[0].cells, row_position=3),
            TableRow(cells=NOUN_GENDER_TABLE.rows[1].cells, row_position=8),
        ],
        noun_table_layout="noun_gender",
    )

    result = generate_fragmented_tables_node(_noun_state(table))

    masculine, feminine = result["fragmented_tables"]
    assert [row["row_position"] for row in masculine["rows"]] == [3, 8]
    assert [row["row_position"] for row in feminine["rows"]] == [3, 8]

    for index, general_row in enumerate(table.rows):
        assert masculine["rows"][index]["cells"] == general_row.cells[:4]
        assert feminine["rows"][index]["cells"] == general_row.cells[4:]


def test_missing_layout_is_not_invented():
    table = NOUN_NUMBER_TABLE.model_copy(update={"noun_table_layout": None})

    result = generate_fragmented_tables_node(_noun_state(table))

    assert [f["noun_table_layout"] for f in result["fragmented_tables"]] == [
        None,
        None,
    ]


def test_malformed_noun_table_is_rejected():
    table = NOUN_NUMBER_TABLE.model_copy(
        update={"headers": NOUN_NUMBER_HEADERS[:7]}
    )

    with pytest.raises(ValueError, match="8 columns"):
        generate_fragmented_tables_node(_noun_state(table))


def test_non_noun_categories_keep_the_llm_fragmentation_path(monkeypatch):
    calls = []

    class FakeChain:
        def invoke(self, payload):
            calls.append(payload)
            return FragmentationOutput(
                should_fragment=True,
                fragmentation_rationale="split by person",
                tables=[
                    TableData(
                        title="First person",
                        headers=["Forma", "Ejemplo"],
                        rows=[TableRow(cells=["hablo", "Hablo mucho."])],
                    )
                ],
            )

    monkeypatch.setattr(node_module, "fragmentation_chain", FakeChain())

    first_table = {
        "title": "First verb table",
        "headers": ["Persona", "Forma", "Ejemplo"],
        "rows": [],
    }
    second_table = {
        "title": "Second verb table",
        "headers": ["Persona", "Forma", "Ejemplo"],
        "rows": [],
    }
    result = generate_fragmented_tables_node(
        {
            "word_category_slug": "verb",
            "general_tables": [first_table, second_table],
        }
    )

    assert calls
    assert json.loads(calls[0]["table_json"]) == first_table
    assert result["should_fragment"] is True
    assert result["fragmented_tables"][0]["title"] == "First person"


class TestAdjectiveFragmentation:
    def test_both_general_tables_split_into_four_fragments(self, monkeypatch):
        monkeypatch.setattr(node_module, "fragmentation_chain", _ExplodingChain())

        result = generate_fragmented_tables_node(_adjective_state())

        assert result["should_fragment"] is True
        singular, plural, masculine, feminine = result["fragmented_tables"]

        assert singular["title"] == f"{ADJ_NUMBER_TABLE.title} — Singular"
        assert plural["title"] == f"{ADJ_NUMBER_TABLE.title} — Plural"
        assert masculine["title"] == f"{ADJ_GENDER_TABLE.title} — Masculino"
        assert feminine["title"] == f"{ADJ_GENDER_TABLE.title} — Femenino"
        assert [f["fragmented_table_id"] for f in (singular, plural, masculine, feminine)] == [1, 2, 3, 4]
        assert [f["adjective_table_layout"] for f in (singular, plural, masculine, feminine)] == ["adj_number_gender"] * 4
        assert [row["cells"] for row in singular["rows"]] == [
            row.cells[:4] for row in ADJ_NUMBER_TABLE.rows
        ]
        assert [row["cells"] for row in plural["rows"]] == [
            row.cells[4:] for row in ADJ_NUMBER_TABLE.rows
        ]
        assert [row["cells"] for row in masculine["rows"]] == [
            row.cells[:4] for row in ADJ_GENDER_TABLE.rows
        ]
        assert [row["cells"] for row in feminine["rows"]] == [
            row.cells[4:] for row in ADJ_GENDER_TABLE.rows
        ]
        assert singular["rows"][0]["cells"][0] == "el libro *rojo*"
        assert plural["rows"][0]["cells"][0] == "los libros *rojos*"
        assert masculine["rows"][0]["cells"][0] == "el chico *alto*"
        assert feminine["rows"][0]["cells"][0] == "la chica *alta*"

    def test_malformed_adjective_table_is_rejected(self):
        table = ADJ_NUMBER_TABLE.model_copy(
            update={"headers": ADJ_NUMBER_HEADERS[:7]}
        )
        state = {
            "word_category_slug": "adjective",
            "general_tables": [table.model_dump()],
        }

        with pytest.raises(ValueError, match="8 columns"):
            generate_fragmented_tables_node(state)


class TestAgreementFragmentation:
    def test_agreement_table_splits_into_masculine_and_feminine(self, monkeypatch):
        monkeypatch.setattr(node_module, "fragmentation_chain", _ExplodingChain())
        state = {
            "word_category_slug": "adjective",
            "general_tables": [ADJ_AGREEMENT_TABLE.model_dump()],
        }

        result = generate_fragmented_tables_node(state)

        assert result["should_fragment"] is True
        masculine, feminine = result["fragmented_tables"]
        assert masculine["title"] == f"{ADJ_AGREEMENT_TABLE.title} — Masculino"
        assert feminine["title"] == f"{ADJ_AGREEMENT_TABLE.title} — Femenino"
        assert [f["fragmented_table_id"] for f in (masculine, feminine)] == [1, 2]
        assert [f["adjective_table_layout"] for f in (masculine, feminine)] == [
            "adj_agreement",
            "adj_agreement",
        ]
        assert [row["cells"] for row in masculine["rows"]] == [
            row.cells[:4] for row in ADJ_AGREEMENT_TABLE.rows
        ]
        assert [row["cells"] for row in feminine["rows"]] == [
            row.cells[4:] for row in ADJ_AGREEMENT_TABLE.rows
        ]
        assert masculine["rows"][0]["cells"][0] == "el libro *rojo*"
        assert feminine["rows"][0]["cells"][0] == "la mesa *roja*"
        assert masculine["rows"][0]["cells"][1] == "the red book"
