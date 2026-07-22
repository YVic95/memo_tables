from uuid import uuid4
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import Session, declarative_base
from models.language import Language
from models.word_categories import WordCategory
from models.grammar_rules import GrammarRule
from models.grammar_rule_translations import GrammarRuleTranslation

def get_word_categories(db: Session):
    return db.query(WordCategory).all()

def create_grammar_rule(
    db: Session,
    title: str,
    description: str,
    language_id: str,
    word_category_id: str,
) -> GrammarRule:
    rule = GrammarRule(
        id=str(uuid4()),
        name=title,
        description=description,
        language_id=language_id,
        word_category_id=word_category_id,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

def get_grammar_rule_by_id(db: Session, rule_id: str) -> GrammarRule | None:
    return db.query(GrammarRule).filter(GrammarRule.id == rule_id).first()

def append_rule_description(db: Session, rule_id: str, content: str) -> GrammarRule | None:
    rule = get_grammar_rule_by_id(db, rule_id)
    if rule is None:
        return None
    rule.description = (rule.description or "") + "\n\n" + content
    db.commit()
    db.refresh(rule)
    return rule

def get_translation_for_rule(db: Session, rule_id: str) -> GrammarRuleTranslation | None:
    return db.query(GrammarRuleTranslation).filter(GrammarRuleTranslation.grammar_rule_id == rule_id).first()

def append_translation_description(db: Session, rule_id: str, content: str) -> GrammarRuleTranslation | None:
    translation = get_translation_for_rule(db, rule_id)
    if translation is None:
        return None
    translation.description = (translation.description or "") + "\n\n" + content
    db.commit()
    db.refresh(translation)
    return translation

def create_translation(
    db: Session,
    grammar_rule_id: str,
    language_id: str,
    name: str,
    description: str,
) -> GrammarRuleTranslation:
    translation = GrammarRuleTranslation(
        id=str(uuid4()),
        grammar_rule_id=grammar_rule_id,
        language_id=language_id,
        name=name,
        description=description,
    )
    db.add(translation)
    db.commit()
    db.refresh(translation)
    return translation