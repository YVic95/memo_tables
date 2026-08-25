import uuid
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from database import Base
from models.language import Language
from models.word_categories import WordCategory
from models.grammar_rules import GrammarRule
from models.base_words import BaseWord
from models.word_translations import WordTranslation
from models.word_rule_assignments import WordRuleAssignment
from models.grammar_rule_rows import GrammarRuleRow
from models.grammar_rule_row_translations import GrammarRuleRowTranslation
from models.word_forms import WordForm
from models.word_form_translations import WordFormTranslation
from models.sentences import Sentence
from models.sentence_translations import SentenceTranslation
from models.word_form_sentences import WordFormSentence

# Register a SQLite-compatible compilation for the PostgreSQL UUID type
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

orig_visit_UUID = SQLiteTypeCompiler.visit_UUID

def _visit_UUID(self, type_, **kw):
    return "VARCHAR"

SQLiteTypeCompiler.visit_UUID = _visit_UUID


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")

    # Enable foreign key support for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def language_es(db_session):
    lang = Language(code="es", name="Spanish")
    db_session.add(lang)
    db_session.commit()
    db_session.refresh(lang)
    return lang


@pytest.fixture()
def language_en(db_session):
    lang = Language(code="en", name="English")
    db_session.add(lang)
    db_session.commit()
    db_session.refresh(lang)
    return lang


@pytest.fixture()
def word_category(db_session):
    cat = WordCategory(name="Nouns", slug="nouns")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


@pytest.fixture()
def grammar_rule(db_session, language_es, word_category):
    rule = GrammarRule(
        name="Noun Gender",
        description="Masculine vs feminine",
        language_id=language_es.id,
        word_category_id=word_category.id,
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule
