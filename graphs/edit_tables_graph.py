"""
    Edits an existing grammar table based on user instructions, in memory.
"""
import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from graphs.states import EditTableState
from graphs.nodes.edit_tables import edit_tables_node

load_dotenv()
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGCHAIN_PROJECT_NAME")

builder = StateGraph(EditTableState)

builder.add_node("edit_tables", edit_tables_node)

builder.add_edge(START, "edit_tables")
builder.add_edge("edit_tables", END)

graph = builder.compile()
