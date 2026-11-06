"""Sortable headers + filter persistence coverage for #68."""

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


def _order(text, *names):
    positions = [text.index(name) for name in names]
    return positions == sorted(positions)


class TestSortHeaders:
    def test_panel_carries_hidden_sort_inputs(self, admin_client, pair_es_en, catalog):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/panel",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 200
        assert 'id="catalogue-sort" name="sort"' in resp.text
        assert 'id="catalogue-dir" name="dir"' in resp.text

    def test_reset_clears_whole_form(self, admin_client, pair_es_en, catalog):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/panel",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert "this.form.reset()" in resp.text

    def test_headers_render_without_arrows_by_default(
        self, admin_client, pair_es_en, catalog
    ):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 200
        assert resp.text.count("sort-header") == 4
        assert "▲" not in resp.text
        assert "▼" not in resp.text

    def test_active_column_shows_arrow_and_toggles(
        self, admin_client, pair_es_en, catalog
    ):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id), "sort": "name", "dir": "asc"},
        )
        assert resp.status_code == 200
        assert "Name ▲" in resp.text
        assert "value='name'" in resp.text
        assert "value='desc'" in resp.text

    def test_desc_arrow_and_toggle_back(self, admin_client, pair_es_en, catalog):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id), "sort": "level", "dir": "desc"},
        )
        assert resp.status_code == 200
        assert "Level ▼" in resp.text
        assert "value='level'" in resp.text
        assert "value='asc'" in resp.text

    def test_headers_link_with_current_filters(
        self, admin_client, pair_es_en, catalog
    ):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id), "level": "A1"},
        )
        assert resp.status_code == 200
        assert "hx-get=\"/admin-panel/canonical-rules/rules?level=A1" in resp.text
        assert "sort=name&amp;dir=asc" in resp.text


class TestSortOrdering:
    def test_sort_name_asc(self, admin_client, pair_es_en, catalog):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id), "sort": "name", "dir": "asc"},
        )
        assert resp.status_code == 200
        assert _order(
            resp.text,
            "Articles",
            "Old Gender Rule",
            "Past Perfect",
            "Plural Nouns",
            "Ser vs Estar",
        )

    def test_sort_name_desc(self, admin_client, pair_es_en, catalog):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id), "sort": "name", "dir": "desc"},
        )
        assert resp.status_code == 200
        assert _order(
            resp.text,
            "Ser vs Estar",
            "Plural Nouns",
            "Past Perfect",
            "Old Gender Rule",
            "Articles",
        )

    def test_sort_combines_with_filter(self, admin_client, pair_es_en, catalog):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={
                "pair_id": str(pair_es_en.pair_id),
                "level": "A1",
                "sort": "name",
                "dir": "desc",
            },
        )
        assert resp.status_code == 200
        assert "Plural Nouns" not in resp.text
        assert _order(resp.text, "Ser vs Estar", "Old Gender Rule", "Articles")

    def test_invalid_sort_falls_back_to_default(
        self, admin_client, pair_es_en, catalog
    ):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id), "sort": "bogus", "dir": "bogus"},
        )
        assert resp.status_code == 200
        assert _order(
            resp.text,
            "Ser vs Estar",
            "Articles",
            "Old Gender Rule",
            "Plural Nouns",
            "Past Perfect",
        )


class TestFilterPersistence:
    def test_deactivate_keeps_level_filter(
        self, admin_client, pair_es_en, catalog
    ):
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")
        resp = admin_client.post(
            f"/admin-panel/canonical-rules/rules/{rule.id}/deactivate",
            data={"level": "A1"},
        )
        assert resp.status_code == 200
        assert "Ser vs Estar" in resp.text
        assert "Articles" in resp.text
        assert "Plural Nouns" not in resp.text
        assert "Past Perfect" not in resp.text

    def test_activate_keeps_status_filter(
        self, admin_client, pair_es_en, catalog
    ):
        rule = next(r for r in catalog if r.slug == "old-gender-rule")
        resp = admin_client.post(
            f"/admin-panel/canonical-rules/rules/{rule.id}/activate",
            data={"status": "active"},
        )
        assert resp.status_code == 200
        assert "Old Gender Rule" in resp.text
        assert "status-badge-active" in resp.text
        assert "No canonical rules match these filters." not in resp.text

    def test_activate_moves_rule_out_of_inactive_view(
        self, admin_client, pair_es_en, catalog
    ):
        rule = next(r for r in catalog if r.slug == "old-gender-rule")
        resp = admin_client.post(
            f"/admin-panel/canonical-rules/rules/{rule.id}/activate",
            data={"status": "inactive"},
        )
        assert resp.status_code == 200
        assert "No canonical rules match these filters." in resp.text

    def test_update_keeps_category_filter(
        self, admin_client, pair_es_en, nouns, catalog
    ):
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")
        resp = admin_client.post(
            f"/admin-panel/canonical-rules/rules/{rule.id}",
            data={
                "word_category_id": str(nouns.id),
                "level": "A2",
                "name": "Ser or Estar",
                "description": "revised description",
                "slug": "ser-or-estar",
                "filter_category": "Nouns",
            },
        )
        assert resp.status_code == 200
        assert "Ser or Estar" in resp.text
        assert "Past Perfect" not in resp.text

    def test_create_keeps_level_filter(
        self, admin_client, pair_es_en, nouns, catalog
    ):
        resp = admin_client.post(
            "/admin-panel/canonical-rules/rules",
            data={
                "pair_id": str(pair_es_en.pair_id),
                "word_category_id": str(nouns.id),
                "level": "A1",
                "name": "Definite Articles",
                "description": "el, la",
                "slug": "definite-articles",
                "filter_level": "A1",
            },
        )
        assert resp.status_code == 200
        assert "Definite Articles" in resp.text
        assert "Plural Nouns" not in resp.text

    def test_toggle_buttons_include_filter_form(
        self, admin_client, pair_es_en, catalog
    ):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 200
        assert 'hx-include="#catalogue-filters"' in resp.text

    def test_create_form_carries_filter_vals(
        self, admin_client, pair_es_en, nouns
    ):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/panel",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 200
        assert "filter_level" in resp.text
        assert "catalogue-filter-level" in resp.text
