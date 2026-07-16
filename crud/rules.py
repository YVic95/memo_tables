from uuid import uuid4
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import Session, declarative_base

Base = declarative_base()

class WordCategory(Base):
    __tablename__ = "word_categories"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False)


class GrammarRule(Base):
    __tablename__ = "grammar_rules"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    language_id = Column(String, ForeignKey("languages.id"), nullable=False)
    word_category_id = Column(String, ForeignKey("word_categories.id"), nullable=False)


class GrammarRuleTranslation(Base):
    __tablename__ = "grammar_rule_translations"

    id = Column(String, primary_key=True)
    grammar_rule_id = Column(String, ForeignKey("grammar_rules.id"), nullable=False)
    language_id = Column(String, ForeignKey("languages.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)

def get_word_categories(db: Session):
    return db.query(WordCategory).all()

def create_grammar_rule(
    db: Session,
    title: str,
    description: str,
    language_id: str,
    word_category_id: str,
) -> str:
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
    return rule.id

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