"""Filter bar UI coverage for #67: panel rendering + HTMX filtering."""

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
from routers.auth import require_admin
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
def nouns(db_session):
    cat = WordCategory(name="Nouns", slug="noun")
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
    return [
        _make_rule(db_session, pair=pair_es_en, category=verbs, level="B1", position=2, name="Past Perfect", slug="past-perfect"),
        _make_rule(db_session, pair=pair_es_en, category=nouns, level="A2", position=1, name="Plural Nouns", slug="plural-nouns"),
        _make_rule(db_session, pair=pair_es_en, category=nouns, level="A1", position=2, name="Articles", slug="articles"),
        _make_rule(db_session, pair=pair_es_en, category=verbs, level="A1", position=1, name="Ser vs Estar", slug="ser-vs-estar"),
        _make_rule(db_session, pair=pair_es_en, category=nouns, level="A1", position=3, name="Old Gender Rule", slug="old-gender-rule", is_active=False),
    ]


class TestFilterBar:
    def test_panel_renders_filter_bar_with_all_options(
        self, admin_client, pair_es_en, nouns, verbs, catalog
    ):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/panel",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 200
        text = resp.text
        assert 'id="catalogue-filters"' in text
        assert 'id="catalogue-filter-level"' in text
        assert 'id="catalogue-filter-category"' in text
        assert 'id="catalogue-filter-status"' in text
        assert 'id="catalogue-filters-reset"' in text
        for level in ("A1", "A2", "B1", "B2", "C1", "C2"):
            assert f'value="{level}"' in text
        assert "Nouns" in text
        assert "Verbs" in text
        assert 'value="active"' in text
        assert 'value="inactive"' in text

    def test_filter_bar_wires_htmx_to_rules_list(
        self, admin_client, pair_es_en, nouns, verbs, catalog
    ):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/panel",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 200
        text = resp.text
        assert 'hx-get="/admin-panel/canonical-rules/rules"' in text
        assert 'hx-target="#canonical-rules-list"' in text
        assert 'hx-include="#canonical-rules-pair-select"' in text
        assert "dispatchEvent(new Event('change'" in text

    def test_category_options_limited_to_pair(
        self, admin_client, db_session, pair_es_en, nouns, verbs, catalog
    ):
        adjectives = WordCategory(name="Adjectives", slug="adjective")
        db_session.add(adjectives)
        db_session.commit()
        resp = admin_client.get(
            "/admin-panel/canonical-rules/panel",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 200
        category_block = resp.text.split('id="catalogue-filter-category"')[1].split(
            "</select>"
        )[0]
        assert "Adjectives" not in category_block
        assert "Nouns" in category_block
        assert "Verbs" in category_block

    def test_no_pair_shows_no_filter_bar(self, admin_client, pair_es_en):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/panel",
            params={"pair_id": ""},
        )
        assert resp.status_code == 200
        assert 'id="catalogue-filters"' not in resp.text


class TestRulesListFiltering:
    def test_level_filter_narrows_rows(self, admin_client, pair_es_en, catalog):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id), "level": "A1"},
        )
        assert resp.status_code == 200
        assert "Ser vs Estar" in resp.text
        assert "Articles" in resp.text
        assert "Plural Nouns" not in resp.text
        assert "Past Perfect" not in resp.text

    def test_status_filter_shows_only_inactive(
        self, admin_client, pair_es_en, catalog
    ):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id), "status": "inactive"},
        )
        assert resp.status_code == 200
        assert "Old Gender Rule" in resp.text
        assert "Ser vs Estar" not in resp.text

    def test_combined_filters(self, admin_client, pair_es_en, catalog):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={
                "pair_id": str(pair_es_en.pair_id),
                "level": "A1",
                "category": "Nouns",
                "status": "active",
            },
        )
        assert resp.status_code == 200
        assert "Articles" in resp.text
        assert "Ser vs Estar" not in resp.text
        assert "Old Gender Rule" not in resp.text

    def test_filtered_to_empty_shows_match_message(
        self, admin_client, pair_es_en, catalog
    ):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id), "level": "C2"},
        )
        assert resp.status_code == 200
        assert "No canonical rules match these filters." in resp.text

    def test_unfiltered_empty_pair_keeps_default_message(
        self, admin_client, pair_es_en
    ):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 200
        assert "No canonical rules for this pair yet." in resp.text


class TestPairChangeKeepsFilters:
    def test_panel_preserves_level_and_status_selections(
        self, admin_client, pair_es_en, catalog
    ):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/panel",
            params={
                "pair_id": str(pair_es_en.pair_id),
                "level": "A1",
                "status": "active",
            },
        )
        assert resp.status_code == 200
        assert '<option value="A1" selected>' in resp.text
        assert '<option value="active" selected>' in resp.text
        assert "Ser vs Estar" in resp.text
        assert "Plural Nouns" not in resp.text

    def test_panel_canonicalizes_category_to_display_name(
        self, admin_client, pair_es_en, catalog
    ):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/panel",
            params={"pair_id": str(pair_es_en.pair_id), "category": "noun"},
        )
        assert resp.status_code == 200
        assert '<option value="Nouns" selected>' in resp.text
        assert "Ser vs Estar" not in resp.text
        assert "Articles" in resp.text

    def test_panel_drops_unknown_category(
        self, admin_client, pair_es_en, catalog
    ):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/panel",
            params={"pair_id": str(pair_es_en.pair_id), "category": "Klingon"},
        )
        assert resp.status_code == 200
        category_block = resp.text.split('id="catalogue-filter-category"')[1].split(
            "</select>"
        )[0]
        assert "selected" not in category_block
        assert "Ser vs Estar" in resp.text

    def test_pair_selector_carries_filters(self, admin_client, pair_es_en):
        resp = admin_client.get("/admin-panel/canonical-rules")
        assert resp.status_code == 200
        assert 'hx-include="#catalogue-filters"' in resp.text
