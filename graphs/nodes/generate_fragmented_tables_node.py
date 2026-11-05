import json
from graphs.llm import llm
from graphs.models import FragmentationOutput, TableData, TableRow
from graphs.prompts import fragmentation_prompt
from graphs.states import GenerateTableState

fragmentation_llm = llm.with_structured_output(FragmentationOutput)
fragmentation_chain = fragmentation_prompt | fragmentation_llm

NOUN_COLUMN_COUNT = 8
NOUN_FRAGMENT_COLUMN_COUNT = NOUN_COLUMN_COUNT // 2
NOUN_SIDE_STARTS = (0, NOUN_FRAGMENT_COLUMN_COUNT)


def _noun_side_fragments(table: dict) -> list[dict]:
    """Split an 8-column noun table into its two 4-column pair sides.

    Column positions are fixed by the noun layouts: the first four columns are
    singular or masculine, the last four are plural or feminine.
    """
    headers = table.get("headers", [])
    rows = table.get("rows", [])
    noun_table_layout = table.get("noun_table_layout")

    if len(headers) != NOUN_COLUMN_COUNT:
        raise ValueError(
            f"Noun table must have {NOUN_COLUMN_COUNT} columns to fragment, "
            f"got {len(headers)}"
        )
    for row in rows:
        if len(row.get("cells", [])) != NOUN_COLUMN_COUNT:
            raise ValueError(
                f"Every noun table row must have {NOUN_COLUMN_COUNT} cells to "
                f"fragment, got {len(row.get('cells', []))}"
            )

    fragments = []

    for fragment_id, start in enumerate(NOUN_SIDE_STARTS, start=1):
        end = start + NOUN_FRAGMENT_COLUMN_COUNT
        side_headers = headers[start:end]
        side_title = (
            f"{table['title']} — {side_headers[0]}"
            if side_headers
            else table["title"]
        )
        fragment_rows = [
            TableRow(
                cells=row.get("cells", [])[start:end],
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
                noun_table_layout=noun_table_layout,
            ).model_dump()
        )

    return fragments


def generate_fragmented_tables_node(state: GenerateTableState) -> GenerateTableState:
    general_table = state["general_table"]

    if state.get("word_category_slug") == "noun":
        return {
            **state,
            "should_fragment": True,
            "fragmented_tables": _noun_side_fragments(general_table),
        }

    result: FragmentationOutput = fragmentation_chain.invoke({
        "general_table_json": json.dumps(general_table, indent=2),
    })

    return {
        **state,
        "should_fragment": result.should_fragment,
        "fragmented_tables": [t.model_dump() for t in result.tables],
    }
