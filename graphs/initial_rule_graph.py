"""
    Initializes a grammar rule by assigning a grammar category, creating database records,
    generating translations, and producing the initial learning content.
"""
import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from graphs.states import InitialRuleState
from graphs.nodes.attach_grammatical_category_to_rule_node import attach_grammatical_category_to_rule_node as category_node
from graphs.nodes.generate_rule_content import generate_rule_content_node as content_node
from graphs.nodes.persist_rule import persist_rule_node
from graphs.nodes.persist_translation import persist_translation_node
from graphs.nodes.translate_rule import translate_rule_node
load_dotenv()
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGCHAIN_PROJECT_NAME")

builder = StateGraph(InitialRuleState)

builder.add_node = ("categorize", category_node)
builder.add_node = ("persist_rule", persist_rule_node)
builder.add_node = ("translate_rule", translate_rule_node)
builder.add_node = ("persist_translation", persist_translation_node)
builder.add_node = ("generate_content", content_node)

builder.add_edge(START, "categorize")
builder.add_edge("categorize", "persist_rule")
builder.add_edge("persist_rule", "translate_rule")
builder.add_edge("translate_rule", "persist_translation")
builder.add_edge("persist_translation", "generate_content")
builder.add_edge("persist_translation", END)

graph = builder.compile()
