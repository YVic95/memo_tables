import uuid
from typing import TypedDict, Optional
from sqlalchemy.orm import Session
from graphs.models import TableData

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
    native_language_id: uuid.UUID
    target_language_id: uuid.UUID
    word_category_id: uuid.UUID
    grammar_rule_id: uuid.UUID
    translated_name: str
    translated_description: str
    full_content: Optional[str]

class GenerateTableState(TypedDict):
    db: Session
    grammar_rule_id: uuid.UUID
    native_language: str
    target_language: str
    rule_name: Optional[str]
    rule_description: Optional[str]
    word_category_slug: Optional[str]
    general_table: Optional[dict]
    should_fragment: Optional[bool]
    fragmented_tables: Optional[list[dict]]

class EditTableState(TypedDict):
    native_language: str
    target_language: str
    instructions: str
    table: dict
    edited_table: Optional[dict]
    edit_history: list[dict]

class SaveTableState(TypedDict):
    db: Session
    language_pair_id: uuid.UUID
    session_id: str
    grammar_rule_id: uuid.UUID
    tables: list[TableData]
    target_language_id: uuid.UUID
    native_language_id: uuid.UUID
    word_category_slug: str
    base_words_to_save: list[dict]
    form_to_base_word_id: dict[str, uuid.UUID]
