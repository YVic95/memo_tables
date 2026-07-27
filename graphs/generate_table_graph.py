import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from graphs.states import GenerateTableState
from graphs.nodes.generate_general_table_node import generate_general_table_node
from graphs.nodes.generate_fragmented_tables_node import generate_fragmented_tables_node

load_dotenv()
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGCHAIN_PROJECT_NAME")

FRAGMENT_THRESHOLD = 3

def route_after_general_table(state: GenerateTableState) -> str:
    table = state["general_table"]
    if table and len(table.get("rows", [])) > FRAGMENT_THRESHOLD:
        return "fragment"
    return END

builder = StateGraph(GenerateTableState)

builder.add_node("generate_general_table", generate_general_table_node)
builder.add_node("generate_fragmented_tables", generate_fragmented_tables_node)

builder.add_edge(START, "generate_general_table")
builder.add_conditional_edges(
    "generate_general_table",
    route_after_general_table,
    {"fragment": "generate_fragmented_tables", END: END},
)
builder.add_edge("generate_fragmented_tables", END)

graph = builder.compile()
