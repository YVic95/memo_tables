import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from graphs.states import SaveTableState
from graphs.nodes.fetch_context_node import fetch_context_node
from graphs.nodes.deduce_base_word_node import deduce_base_word_node
from graphs.nodes.save_base_word_node import save_base_word_node
from graphs.nodes.translate_base_words_node import translate_base_words_node
from graphs.nodes.process_all_tables_node import process_all_tables_node

load_dotenv()
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGCHAIN_PROJECT_NAME")

builder = StateGraph(SaveTableState)

builder.add_node("fetch_context", fetch_context_node)
builder.add_node("deduce_base_word", deduce_base_word_node)
builder.add_node("save_base_word", save_base_word_node)
builder.add_node("translate_base_words", translate_base_words_node)
builder.add_node("process_all_tables", process_all_tables_node)

builder.add_edge(START, "fetch_context")
builder.add_edge("fetch_context", "deduce_base_word")
builder.add_edge("deduce_base_word", "translate_base_words")
builder.add_edge("translate_base_words", "save_base_word")
builder.add_edge("save_base_word", "process_all_tables")
builder.add_edge("process_all_tables", END)

graph = builder.compile()