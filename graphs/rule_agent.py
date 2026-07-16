import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from graphs.states import RuleCreationAgentState
from graphs.nodes.propose_rules_nodes import propose_rules_node

load_dotenv()
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGCHAIN_PROJECT_NAME")

graph_builder = StateGraph(RuleCreationAgentState)

graph_builder.add_node("propose_rules", propose_rules_node)
graph_builder.add_edge(START, "propose_rules")
graph_builder.add_edge("propose_rules", END)

graph = graph_builder.compile()