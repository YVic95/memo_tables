import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from graphs.states import GenerateTableState
from graphs.nodes.fetch_rule_category_node import fetch_rule_category_node
from graphs.nodes.generate_category_table_node import generate_category_table_node
from graphs.nodes.generate_general_table_node import generate_general_table_node
from graphs.nodes.generate_fragmented_tables_node import generate_fragmented_tables_node

load_dotenv()
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGCHAIN_PROJECT_NAME")

FRAGMENT_THRESHOLD = 3

CATEGORY_ROUTES = {
    "verb": "generate_category_table",
    "noun": "generate_category_table",
    "pronoun": "generate_category_table",
    "adjective": "generate_category_table",
    "adverb": "generate_category_table",
}

def route_by_category(state: GenerateTableState) -> str:
    slug = state.get("word_category_slug", "")
    return CATEGORY_ROUTES.get(slug, "generate_general_table")


def route_after_table(state: GenerateTableState) -> str:
    table = state["general_table"]
    if table and len(table.get("rows", [])) > FRAGMENT_THRESHOLD:
        return "fragment"
    return END

builder = StateGraph(GenerateTableState)

builder.add_node("fetch_rule_category", fetch_rule_category_node)
builder.add_node("generate_category_table", generate_category_table_node)
builder.add_node("generate_general_table", generate_general_table_node)
builder.add_node("generate_fragmented_tables", generate_fragmented_tables_node)

builder.add_edge(START, "fetch_rule_category")
builder.add_conditional_edges(
    "fetch_rule_category",
    route_by_category,
    {
        "generate_category_table": "generate_category_table",
        "generate_general_table": "generate_general_table",
    },
)
builder.add_conditional_edges(
    "generate_category_table",
    route_after_table,
    {"fragment": "generate_fragmented_tables", END: END},
)
builder.add_conditional_edges(
    "generate_general_table",
    route_after_table,
    {"fragment": "generate_fragmented_tables", END: END},
)
builder.add_edge("generate_fragmented_tables", END)

graph = builder.compile()
