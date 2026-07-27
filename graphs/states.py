from typing import TypedDict, Optional
from sqlalchemy.orm import Session

class RuleCreationAgentState(TypedDict):
    native_language: str
    target_language: str
    proposed_rules: list[dict]

class InitialRuleState(TypedDict):
    db: Session
    rule_title: str
    rule_explanation: str
    native_language: str
    target_language: str
    native_language_id: str
    target_language_id: str
    word_category_id: str
    grammar_rule_id: str
    translated_name: str
    translated_description: str
    full_content: Optional[str]

class GenerateTableState(TypedDict):
    db: Session
    grammar_rule_id: str
    native_language: str
    target_language: str
    rule_name: Optional[str]
    rule_description: Optional[str]
    general_table: Optional[dict]
    should_fragment: Optional[bool]
    fragmented_tables: Optional[list[dict]]