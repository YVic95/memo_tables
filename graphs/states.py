from typing import TypedDict

class RuleCreationAgentState(TypedDict):
    native_language: str
    target_language: str
    proposed_rules: list[dict]