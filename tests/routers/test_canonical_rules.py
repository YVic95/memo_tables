import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from models.canonical_rules import CanonicalRule
from models.language import Language
from models.language_pairs import LanguagePair
from models.word_categories import WordCategory
from routers.auth import get_current_user, require_admin
from serve import app

from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

def _visit_JSONB(self, type_, **kw):
    return "TEXT"

SQLiteTypeCompiler.visit_JSONB = _visit_JSONB


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    yield session
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    session.close()


@pytest.fixture()
def admin_client(db_session):
    app.dependency_overrides[require_admin] = lambda: {
        "email": "admin@example.com",
        "app_metadata": {"role": "admin"},
    }
    yield TestClient(app, follow_redirects=False)
    app.dependency_overrides.clear()


@pytest.fixture()
def non_admin_client(db_session):
    app.dependency_overrides[get_current_user] = lambda: {
        "email": "user@example.com",
        "app_metadata": {"role": "user"},
    }
    yield TestClient(app, follow_redirects=False)
    app.dependency_overrides.clear()


@pytest.fixture()
def pair_es_en(db_session):
    lang_es = Language(code="es", name="Spanish")
    lang_en = Language(code="en", name="English")
    db_session.add_all([lang_es, lang_en])
    db_session.commit()

    pair = LanguagePair(native_language_id=lang_en.id, target_language_id=lang_es.id)
    db_session.add(pair)
    db_session.commit()
    db_session.refresh(pair)
    return pair


@pytest.fixture()
def pair_de_es(db_session):
    lang_de = Language(code="de", name="German")
    lang_es = Language(code="es", name="Spanish")
    db_session.add_all([lang_de, lang_es])
    db_session.commit()

    pair = LanguagePair(native_language_id=lang_es.id, target_language_id=lang_de.id)
    db_session.add(pair)
    db_session.commit()
    db_session.refresh(pair)
    return pair


@pytest.fixture()
def nouns(db_session):
    cat = WordCategory(name="Nouns", slug="nouns")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


@pytest.fixture()
def verbs(db_session):
    cat = WordCategory(name="Verbs", slug="verbs")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


def _make_rule(db, *, pair, category, level, position, name, slug, is_active=True):
    rule = CanonicalRule(
        native_language_id=pair.native_language_id,
        target_language_id=pair.target_language_id,
        word_category_id=category.id,
        level=level,
        name=name,
        description=f"Description of {name}",
        position=position,
        slug=slug,
        is_active=is_active,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@pytest.fixture()
def catalog(db_session, pair_es_en, nouns, verbs):
    """Unordered catalog rows exercising level/position ordering and inactive flags."""
    return [
        _make_rule(db_session, pair=pair_es_en, category=verbs, level="B1", position=2, name="Past Perfect", slug="past-perfect"),
        _make_rule(db_session, pair=pair_es_en, category=nouns, level="A2", position=1, name="Plural Nouns", slug="plural-nouns"),
        _make_rule(db_session, pair=pair_es_en, category=nouns, level="A1", position=2, name="Articles", slug="articles"),
        _make_rule(db_session, pair=pair_es_en, category=verbs, level="A1", position=1, name="Ser vs Estar", slug="ser-vs-estar"),
        _make_rule(db_session, pair=pair_es_en, category=nouns, level="A1", position=3, name="Old Gender Rule", slug="old-gender-rule", is_active=False),
    ]


class TestSection:
    def test_direct_navigation_renders_full_page_with_selector(self, admin_client):
        resp = admin_client.get("/admin-panel/canonical-rules")
        assert resp.status_code == 200
        assert "<html" in resp.text
        assert "Canonical Rules" in resp.text
        assert 'id="canonical-rules-pair-select"' in resp.text
        assert "Select a language pair to view its canonical rules." in resp.text

    def test_htmx_navigation_renders_fragment(self, admin_client):
        resp = admin_client.get(
            "/admin-panel/canonical-rules",
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        assert "<html" not in resp.text
        assert 'id="canonical-rules-pair-select"' in resp.text
        assert "Select a language pair to view its canonical rules." in resp.text

    def test_section_lists_available_pairs(self, admin_client, pair_es_en, pair_de_es):
        resp = admin_client.get("/admin-panel/canonical-rules")
        assert resp.status_code == 200
        assert "English" in resp.text
        assert "Spanish" in resp.text
        assert "German" in resp.text

    def test_section_rejects_non_admin(self, non_admin_client):
        resp = non_admin_client.get("/admin-panel/canonical-rules")
        assert resp.status_code == 307
        assert resp.headers["location"] == "/login"

    def test_section_rejects_unauthenticated(self, db_session):
        client = TestClient(app, follow_redirects=False)
        resp = client.get("/admin-panel/canonical-rules")
        assert resp.status_code == 307
        assert resp.headers["location"] == "/login"


class TestRulesList:
    def test_ordered_by_level_then_position(self, admin_client, db_session, pair_es_en, catalog):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 200
        text = resp.text
        order = [
            text.index("Ser vs Estar"),
            text.index("Articles"),
            text.index("Old Gender Rule"),
            text.index("Plural Nouns"),
            text.index("Past Perfect"),
        ]
        assert order == sorted(order)

    def test_each_row_shows_all_fields(self, admin_client, pair_es_en, catalog):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 200
        text = resp.text
        assert "Ser vs Estar" in text
        assert "ser-vs-estar" in text
        assert "A1" in text
        assert "Verbs" in text
        assert "Nouns" in text
        row = text[text.index("Ser vs Estar"):]
        row = row[: row.index("</tr>")]
        assert ">1<" in row  # position
        assert "status-badge-active" in row

    def test_inactive_rule_shows_inactive_badge(self, admin_client, pair_es_en, catalog):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 200
        row_html = resp.text
        # the inactive fixture row carries its own badge class
        assert "Old Gender Rule" in row_html
        assert "status-badge-inactive" in row_html
        assert "status-badge-active" in row_html
        # count badges: 5 rows -> at least one inactive, rest active
        assert row_html.count("status-badge-inactive") >= 1

    def test_active_rules_show_active_badge(self, admin_client, db_session, pair_es_en, nouns):
        rule = _make_rule(db_session, pair=pair_es_en, category=nouns, level="A1", position=1, name="Only Rule", slug="only-rule", is_active=True)
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 200
        assert "status-badge-active" in resp.text
        assert "status-badge-inactive" not in resp.text
        assert "Active" in resp.text

    def test_empty_pair_shows_empty_state(self, admin_client, pair_es_en):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 200
        assert "No canonical rules" in resp.text

    def test_unknown_pair_shows_not_found_message(self, admin_client):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 200
        assert "Language pair not found" in resp.text

    def test_list_scoped_to_selected_pair(self, admin_client, db_session, pair_es_en, pair_de_es, nouns, catalog):
        _make_rule(db_session, pair=pair_de_es, category=nouns, level="A1", position=1, name="German Only Rule", slug="german-only-rule")
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 200
        assert "Ser vs Estar" in resp.text
        assert "German Only Rule" not in resp.text

    def test_list_rejects_non_admin(self, non_admin_client, pair_es_en):
        resp = non_admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 307
        assert resp.headers["location"] == "/login"

    def test_list_rejects_unauthenticated(self, db_session, pair_es_en):
        client = TestClient(app, follow_redirects=False)
        resp = client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 307
        assert resp.headers["location"] == "/login"
