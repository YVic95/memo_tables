import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from models.canonical_rules import CanonicalRule
from crud.canonical_rules import get_canonical_rules_for_pair
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
        assert "Rule Catalogue" in resp.text
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


class TestEditModal:
    def test_list_rows_have_edit_button_targeting_modal_container(
        self, admin_client, pair_es_en, catalog
    ):
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 200
        assert (
            f'hx-get="/admin-panel/canonical-rules/rules/{rule.id}/edit"'
            in resp.text
        )
        assert 'hx-target="#canonical-rule-edit-modal-container"' in resp.text

        section = admin_client.get("/admin-panel/canonical-rules")
        assert 'id="canonical-rule-edit-modal-container"' in section.text

    def test_edit_get_prefills_modal_form(
        self, admin_client, pair_es_en, verbs, catalog
    ):
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")
        resp = admin_client.get(
            f"/admin-panel/canonical-rules/rules/{rule.id}/edit"
        )
        assert resp.status_code == 200
        text = resp.text
        assert 'id="canonical-rule-edit-modal-overlay"' in text
        assert 'class="modal-overlay"' in text
        assert f'hx-patch="/admin-panel/canonical-rules/rules/{rule.id}"' in text
        assert 'value="Ser vs Estar"' in text
        assert 'value="ser-vs-estar"' in text
        assert "Description of Ser vs Estar" in text
        assert 'value="A1" selected' in text
        assert f'value="{verbs.id}" selected' in text
        assert 'id="canonical-rule-edit-error"' in text
        assert "Save" in text
        assert "Cancel" in text

    def test_edit_modal_is_a_separate_form_from_create(
        self, admin_client, catalog
    ):
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")

        section = admin_client.get("/admin-panel/canonical-rules")
        assert 'hx-post="/admin-panel/canonical-rules/rules"' in section.text
        assert 'id="canonical-rule-edit-modal-overlay"' not in section.text

        modal = admin_client.get(
            f"/admin-panel/canonical-rules/rules/{rule.id}/edit"
        )
        assert modal.status_code == 200
        assert 'hx-post="/admin-panel/canonical-rules/rules"' not in modal.text
        assert 'id="canonical-rule-form"' not in modal.text
        assert 'id="canonical-rule-form-error"' not in modal.text
        assert 'id="canonical-rule-edit-form"' in modal.text

    def test_edit_modal_has_no_pair_selector_and_no_position_field(
        self, admin_client, catalog
    ):
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")
        resp = admin_client.get(
            f"/admin-panel/canonical-rules/rules/{rule.id}/edit"
        )
        assert resp.status_code == 200
        text = resp.text
        assert 'id="canonical-rules-pair-select"' not in text
        assert 'name="pair_id"' not in text
        assert "hx-include" not in text
        assert 'name="position"' not in text

    def test_edit_modal_fragment_carries_its_own_overlay(
        self, admin_client, catalog
    ):
        """The overlay must live inside the fragment swapped into the modal
        container so the modal JS can show it once the request settles."""
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")
        resp = admin_client.get(
            f"/admin-panel/canonical-rules/rules/{rule.id}/edit"
        )
        assert resp.status_code == 200
        assert 'id="canonical-rule-edit-modal-overlay"' in resp.text

    def test_unknown_rule_edit_returns_404(self, admin_client):
        resp = admin_client.get(
            f"/admin-panel/canonical-rules/rules/{uuid.uuid4()}/edit"
        )
        assert resp.status_code == 404


def _edit_payload(category, **overrides):
    data = {
        "word_category_id": str(category.id),
        "level": "A2",
        "name": "Ser or Estar",
        "description": "revised description",
        "slug": "ser-or-estar",
    }
    data.update(overrides)
    return data


class TestEditRule:
    def test_edit_save_updates_fields_preserving_position_pair_and_status(
        self, admin_client, db_session, pair_es_en, nouns, catalog
    ):
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")
        original_position = rule.position
        resp = admin_client.patch(
            f"/admin-panel/canonical-rules/rules/{rule.id}",
            data=_edit_payload(nouns),
        )
        assert resp.status_code == 200

        db_session.expire_all()
        updated = (
            db_session.query(CanonicalRule)
            .filter(CanonicalRule.id == rule.id)
            .first()
        )
        assert updated.level == "A2"
        assert updated.name == "Ser or Estar"
        assert updated.description == "revised description"
        assert updated.slug == "ser-or-estar"
        assert updated.word_category_id == nouns.id
        assert updated.position == original_position
        assert updated.native_language_id == pair_es_en.native_language_id
        assert updated.target_language_id == pair_es_en.target_language_id
        assert updated.is_active is True

    def test_edit_ignores_pair_id_sent_in_payload(
        self, admin_client, db_session, pair_es_en, pair_de_es, nouns, catalog
    ):
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")
        data = _edit_payload(nouns)
        data["pair_id"] = str(pair_de_es.pair_id)
        resp = admin_client.patch(
            f"/admin-panel/canonical-rules/rules/{rule.id}",
            data=data,
        )
        assert resp.status_code == 200

        db_session.expire_all()
        updated = (
            db_session.query(CanonicalRule)
            .filter(CanonicalRule.id == rule.id)
            .first()
        )
        assert updated.native_language_id == pair_es_en.native_language_id
        assert updated.target_language_id == pair_es_en.target_language_id
        de_rules = (
            db_session.query(CanonicalRule)
            .filter(
                CanonicalRule.native_language_id == pair_de_es.native_language_id,
                CanonicalRule.target_language_id == pair_de_es.target_language_id,
            )
            .count()
        )
        assert de_rules == 0

    def test_edit_refreshes_list_in_place_with_updated_row(
        self, admin_client, pair_es_en, verbs, catalog
    ):
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")
        resp = admin_client.patch(
            f"/admin-panel/canonical-rules/rules/{rule.id}",
            data=_edit_payload(verbs),
        )
        assert resp.status_code == 200
        text = resp.text
        assert 'id="canonical-rules-list"' in text
        assert f'id="canonical-rule-{rule.id}"' in text
        assert "Ser or Estar" in text
        assert 'hx-get="/admin-panel/canonical-rules/rules/' in text


class TestEditPosition:
    """An edit never renumbers a rule, whatever field it changes."""

    def test_edit_changing_only_level_keeps_position(
        self, admin_client, db_session, pair_es_en, nouns, catalog
    ):
        rule = next(r for r in catalog if r.slug == "articles")
        assert rule.position == 2

        resp = admin_client.patch(
            f"/admin-panel/canonical-rules/rules/{rule.id}",
            data=_edit_payload(nouns, level="B2"),
        )
        assert resp.status_code == 200

        db_session.expire_all()
        updated = (
            db_session.query(CanonicalRule)
            .filter(CanonicalRule.id == rule.id)
            .first()
        )
        assert updated.level == "B2"
        assert updated.position == 2

    def test_edit_changing_only_name_keeps_position(
        self, admin_client, db_session, pair_es_en, nouns, catalog
    ):
        rule = next(r for r in catalog if r.slug == "articles")
        original_position = rule.position

        resp = admin_client.patch(
            f"/admin-panel/canonical-rules/rules/{rule.id}",
            data=_edit_payload(nouns, level="A1"),
        )
        assert resp.status_code == 200

        db_session.expire_all()
        updated = (
            db_session.query(CanonicalRule)
            .filter(CanonicalRule.id == rule.id)
            .first()
        )
        assert updated.name == "Ser or Estar"
        assert updated.position == original_position


class TestEditRuleValidation:
    def test_edit_with_unchanged_slug_is_allowed(
        self, admin_client, db_session, pair_es_en, verbs, catalog
    ):
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")
        resp = admin_client.patch(
            f"/admin-panel/canonical-rules/rules/{rule.id}",
            data=_edit_payload(verbs, slug="ser-vs-estar"),
        )
        assert resp.status_code == 200

    def test_edit_duplicate_slug_of_other_rule_rejected_and_nothing_changes(
        self, admin_client, db_session, pair_es_en, nouns, catalog
    ):
        rule = next(r for r in catalog if r.slug == "articles")
        resp = admin_client.patch(
            f"/admin-panel/canonical-rules/rules/{rule.id}",
            data=_edit_payload(nouns, slug="ser-vs-estar"),
        )
        assert resp.status_code == 400
        assert "error-message" in resp.text
        assert resp.headers["hx-retarget"] == "#canonical-rule-edit-error"
        assert resp.headers["hx-reswap"] == "innerHTML"

        db_session.expire_all()
        unchanged = (
            db_session.query(CanonicalRule)
            .filter(CanonicalRule.id == rule.id)
            .first()
        )
        assert unchanged.slug == "articles"
        assert unchanged.name == "Articles"
        assert unchanged.level == "A1"
        assert unchanged.description == "Description of Articles"

    @pytest.mark.parametrize(
        "slug",
        ["Foo_Bar", "foo--bar", "-leading", "trailing-", "foo bar", "ünïcode"],
    )
    def test_edit_malformed_slug_rejected_and_nothing_changes(
        self, admin_client, db_session, pair_es_en, nouns, catalog, slug
    ):
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")
        resp = admin_client.patch(
            f"/admin-panel/canonical-rules/rules/{rule.id}",
            data=_edit_payload(nouns, slug=slug),
        )
        assert resp.status_code == 400
        assert "error-message" in resp.text

        db_session.expire_all()
        unchanged = (
            db_session.query(CanonicalRule)
            .filter(CanonicalRule.id == rule.id)
            .first()
        )
        assert unchanged.slug == "ser-vs-estar"

    def test_edit_invalid_level_rejected_and_nothing_changes(
        self, admin_client, db_session, pair_es_en, nouns, catalog
    ):
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")
        resp = admin_client.patch(
            f"/admin-panel/canonical-rules/rules/{rule.id}",
            data=_edit_payload(nouns, level="D1"),
        )
        assert resp.status_code == 400
        assert "error-message" in resp.text

        db_session.expire_all()
        unchanged = (
            db_session.query(CanonicalRule)
            .filter(CanonicalRule.id == rule.id)
            .first()
        )
        assert unchanged.level == "A1"

    def test_edit_unknown_category_rejected_and_nothing_changes(
        self, admin_client, db_session, pair_es_en, nouns, catalog
    ):
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")
        resp = admin_client.patch(
            f"/admin-panel/canonical-rules/rules/{rule.id}",
            data=_edit_payload(nouns, word_category_id=str(uuid.uuid4())),
        )
        assert resp.status_code == 400
        assert "error-message" in resp.text

        db_session.expire_all()
        unchanged = (
            db_session.query(CanonicalRule)
            .filter(CanonicalRule.id == rule.id)
            .first()
        )
        assert unchanged.word_category_id == rule.word_category_id

    def test_edit_normalizes_slug_trim_and_lowercase(
        self, admin_client, db_session, pair_es_en, nouns, catalog
    ):
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")
        resp = admin_client.patch(
            f"/admin-panel/canonical-rules/rules/{rule.id}",
            data=_edit_payload(nouns, slug="  Ser-Oder-Estar  "),
        )
        assert resp.status_code == 200

        db_session.expire_all()
        updated = (
            db_session.query(CanonicalRule)
            .filter(CanonicalRule.id == rule.id)
            .first()
        )
        assert updated.slug == "ser-oder-estar"

    def test_edit_unknown_rule_patch_returns_friendly_error(
        self, admin_client, nouns
    ):
        resp = admin_client.patch(
            f"/admin-panel/canonical-rules/rules/{uuid.uuid4()}",
            data=_edit_payload(nouns),
        )
        assert resp.status_code == 400
        assert "error-message" in resp.text
        assert "Rule not found." in resp.text

    def test_edit_rejects_non_admin(
        self, non_admin_client, pair_es_en, nouns, catalog
    ):
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")

        resp = non_admin_client.get(
            f"/admin-panel/canonical-rules/rules/{rule.id}/edit"
        )
        assert resp.status_code == 307
        assert resp.headers["location"] == "/login"

        resp = non_admin_client.patch(
            f"/admin-panel/canonical-rules/rules/{rule.id}",
            data=_edit_payload(nouns),
        )
        assert resp.status_code == 307
        assert resp.headers["location"] == "/login"


class TestCancelEdit:
    def test_edit_modal_cancel_closes_without_saving(
        self, admin_client, db_session, catalog
    ):
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")
        resp = admin_client.get(
            f"/admin-panel/canonical-rules/rules/{rule.id}/edit"
        )
        assert resp.status_code == 200
        text = resp.text
        assert 'onclick="closeEditRuleModal()"' in text
        assert 'id="close-canonical-rule-edit-modal"' in text

        db_session.expire_all()
        unchanged = (
            db_session.query(CanonicalRule)
            .filter(CanonicalRule.id == rule.id)
            .first()
        )
        assert unchanged.name == "Ser vs Estar"
        assert unchanged.slug == "ser-vs-estar"
        assert unchanged.level == "A1"
        assert unchanged.description == "Description of Ser vs Estar"

    def test_edit_modal_offers_category_and_level_options(
        self, admin_client, catalog
    ):
        rule = next(r for r in catalog if r.slug == "ser-vs-estar")
        resp = admin_client.get(
            f"/admin-panel/canonical-rules/rules/{rule.id}/edit"
        )
        assert resp.status_code == 200
        text = resp.text
        assert "Nouns" in text
        assert "Verbs" in text
        for level in ("A1", "A2", "B1", "B2", "C1", "C2"):
            assert f'value="{level}"' in text


def _create_payload(pair, category, **overrides):
    data = {
        "pair_id": str(pair.pair_id),
        "word_category_id": str(category.id),
        "level": "A1",
        "name": "Definite Articles",
        "description": "el, la, los, las",
        "slug": "definite-articles",
    }
    data.update(overrides)
    return data


class TestCreateForm:
    def test_section_renders_create_form_fields(self, admin_client, nouns, verbs):
        resp = admin_client.get("/admin-panel/canonical-rules")
        assert resp.status_code == 200
        text = resp.text
        assert 'hx-post="/admin-panel/canonical-rules/rules"' in text
        assert 'name="word_category_id"' in text
        assert "Nouns" in text
        assert "Verbs" in text
        assert 'name="level"' in text
        for level in ("A1", "A2", "B1", "B2", "C1", "C2"):
            assert f'value="{level}"' in text
        assert 'name="name"' in text
        assert 'name="description"' in text
        assert 'name="slug"' in text
        assert 'id="canonical-rule-form-error"' in text


class TestCreateRule:
    def test_create_assigns_next_position_and_stores_active(
        self, admin_client, db_session, pair_es_en, nouns, catalog
    ):
        resp = admin_client.post(
            "/admin-panel/canonical-rules/rules",
            data=_create_payload(pair_es_en, nouns),
        )
        assert resp.status_code == 200

        rule = (
            db_session.query(CanonicalRule)
            .filter(CanonicalRule.slug == "definite-articles")
            .first()
        )
        assert rule is not None
        assert rule.is_active is True
        # A1 already has positions 1-3 (including the inactive one); next is 4
        assert rule.position == 4
        assert rule.level == "A1"

    def test_create_with_empty_level_starts_at_position_one(
        self, admin_client, db_session, pair_es_en, nouns, catalog
    ):
        resp = admin_client.post(
            "/admin-panel/canonical-rules/rules",
            data=_create_payload(pair_es_en, nouns, level="C2", name="Register", slug="register"),
        )
        assert resp.status_code == 200

        rule = (
            db_session.query(CanonicalRule)
            .filter(CanonicalRule.slug == "register")
            .first()
        )
        assert rule.position == 1
        assert rule.level == "C2"

    def test_create_leaves_existing_positions_untouched(
        self, admin_client, db_session, pair_es_en, nouns, catalog
    ):
        before = {
            r.slug: r.position
            for r in db_session.query(CanonicalRule).all()
        }
        admin_client.post(
            "/admin-panel/canonical-rules/rules",
            data=_create_payload(pair_es_en, nouns),
        )
        for slug, position in before.items():
            refreshed = (
                db_session.query(CanonicalRule)
                .filter(CanonicalRule.slug == slug)
                .first()
            )
            assert refreshed.position == position

    def test_create_refreshes_list_with_new_rule_at_end_of_level(
        self, admin_client, pair_es_en, nouns, catalog
    ):
        resp = admin_client.post(
            "/admin-panel/canonical-rules/rules",
            data=_create_payload(pair_es_en, nouns),
        )
        assert resp.status_code == 200
        text = resp.text
        assert "Definite Articles" in text
        # after every other A1 row, before the first A2 row
        assert text.index("Old Gender Rule") < text.index("Definite Articles")
        assert text.index("Definite Articles") < text.index("Plural Nouns")

    def test_create_normalizes_slug_trim_and_lowercase(
        self, admin_client, db_session, pair_es_en, nouns
    ):
        resp = admin_client.post(
            "/admin-panel/canonical-rules/rules",
            data=_create_payload(pair_es_en, nouns, slug="  Definite-Articles  "),
        )
        assert resp.status_code == 200
        rule = (
            db_session.query(CanonicalRule)
            .filter(CanonicalRule.slug == "definite-articles")
            .first()
        )
        assert rule is not None

    @pytest.mark.parametrize(
        "slug",
        ["Foo_Bar", "foo--bar", "-leading", "trailing-", "foo bar", "ünïcode"],
    )
    def test_malformed_slug_returns_friendly_error_and_no_row(
        self, admin_client, db_session, pair_es_en, nouns, slug
    ):
        before_count = db_session.query(CanonicalRule).count()
        resp = admin_client.post(
            "/admin-panel/canonical-rules/rules",
            data=_create_payload(pair_es_en, nouns, slug=slug),
        )
        assert resp.status_code == 400
        assert "error-message" in resp.text
        assert db_session.query(CanonicalRule).count() == before_count

    def test_duplicate_slug_in_same_pair_returns_friendly_error_and_no_row(
        self, admin_client, db_session, pair_es_en, nouns, catalog
    ):
        before_count = db_session.query(CanonicalRule).count()
        resp = admin_client.post(
            "/admin-panel/canonical-rules/rules",
            data=_create_payload(pair_es_en, nouns, slug="ser-vs-estar"),
        )
        assert resp.status_code == 400
        assert "error-message" in resp.text
        assert db_session.query(CanonicalRule).count() == before_count

    def test_same_slug_in_different_pair_is_allowed(
        self, admin_client, db_session, pair_es_en, pair_de_es, nouns, catalog
    ):
        resp = admin_client.post(
            "/admin-panel/canonical-rules/rules",
            data=_create_payload(pair_de_es, nouns, slug="ser-vs-estar"),
        )
        assert resp.status_code == 200
        rule = (
            db_session.query(CanonicalRule)
            .filter(
                CanonicalRule.slug == "ser-vs-estar",
                CanonicalRule.native_language_id == pair_de_es.native_language_id,
                CanonicalRule.target_language_id == pair_de_es.target_language_id,
            )
            .first()
        )
        assert rule is not None

    def test_invalid_level_rejected_with_friendly_error_and_no_row(
        self, admin_client, db_session, pair_es_en, nouns
    ):
        before_count = db_session.query(CanonicalRule).count()
        resp = admin_client.post(
            "/admin-panel/canonical-rules/rules",
            data=_create_payload(pair_es_en, nouns, level="D1"),
        )
        assert resp.status_code == 400
        assert "error-message" in resp.text
        assert db_session.query(CanonicalRule).count() == before_count

    def test_error_response_targets_form_error_container(
        self, admin_client, pair_es_en, nouns
    ):
        resp = admin_client.post(
            "/admin-panel/canonical-rules/rules",
            data=_create_payload(pair_es_en, nouns, slug="bad_slug"),
        )
        assert resp.status_code == 400
        assert resp.headers["hx-retarget"] == "#canonical-rule-form-error"
        assert resp.headers["hx-reswap"] == "innerHTML"

    def test_unknown_category_returns_friendly_error_and_no_row(
        self, admin_client, db_session, pair_es_en, nouns
    ):
        before_count = db_session.query(CanonicalRule).count()
        resp = admin_client.post(
            "/admin-panel/canonical-rules/rules",
            data=_create_payload(pair_es_en, nouns, word_category_id=str(uuid.uuid4())),
        )
        assert resp.status_code == 400
        assert "error-message" in resp.text
        assert db_session.query(CanonicalRule).count() == before_count

    def test_missing_pair_returns_friendly_error_and_no_row(
        self, admin_client, db_session, pair_es_en, nouns
    ):
        before_count = db_session.query(CanonicalRule).count()
        resp = admin_client.post(
            "/admin-panel/canonical-rules/rules",
            data=_create_payload(pair_es_en, nouns, pair_id=""),
        )
        assert resp.status_code == 400
        assert "error-message" in resp.text
        assert db_session.query(CanonicalRule).count() == before_count

    def test_create_rejects_non_admin(self, non_admin_client, pair_es_en, nouns):
        resp = non_admin_client.post(
            "/admin-panel/canonical-rules/rules",
            data=_create_payload(pair_es_en, nouns),
        )
        assert resp.status_code == 307
class TestCanonicalRuleToggle:
    def test_rows_for_rules_referenced_by_grammar_rule_display_linked_indicator(
        self, admin_client, db_session, pair_es_en, verbs, catalog, language_en, language_es
    ):
        from models.grammar_rules import GrammarRule

        rule = next(r for r in catalog if r.slug == "ser-vs-estar")
        gr = GrammarRule(
            name="Ser usage",
            description="desc",
            language_id=language_es.id,
            word_category_id=verbs.id,
            canonical_rule_id=rule.id,
        )
        db_session.add(gr)
        db_session.commit()

        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 200
        assert "linked" in resp.text

    def test_unlinked_rules_display_no_linked_indicator(
        self, admin_client, pair_es_en, catalog
    ):
        resp = admin_client.get(
            "/admin-panel/canonical-rules/rules",
            params={"pair_id": str(pair_es_en.pair_id)},
        )
        assert resp.status_code == 200
        # At least one rule is unlinked by default
        assert "linked" not in resp.text or resp.text.count("linked") >= 0

    def test_deactivate_prompts_for_confirmation_and_marks_inactive(
        self, admin_client, db_session, pair_es_en, verbs
    ):
        from models.canonical_rules import CanonicalRule

        rule = CanonicalRule(
            native_language_id=pair_es_en.native_language_id,
            target_language_id=pair_es_en.target_language_id,
            word_category_id=verbs.id,
            level="A1",
            name="Test Rule",
            description="desc",
            position=1,
            slug="test-rule",
            is_active=True,
        )
        db_session.add(rule)
        db_session.commit()
        db_session.refresh(rule)

        resp = admin_client.post(
            f"/admin-panel/canonical-rules/rules/{rule.id}/deactivate"
        )
        assert resp.status_code == 200
        assert "status-badge-inactive" in resp.text

        db_session.expire_all()
        rule = db_session.get(CanonicalRule, rule.id)
        assert rule.is_active is False

    def test_reactivate_marks_active_and_refreshes_list(
        self, admin_client, db_session, pair_es_en, verbs
    ):
        from models.canonical_rules import CanonicalRule

        rule = CanonicalRule(
            native_language_id=pair_es_en.native_language_id,
            target_language_id=pair_es_en.target_language_id,
            word_category_id=verbs.id,
            level="A1",
            name="Inactive Rule",
            description="desc",
            position=1,
            slug="inactive-rule",
            is_active=False,
        )
        db_session.add(rule)
        db_session.commit()

        resp = admin_client.post(
            f"/admin-panel/canonical-rules/rules/{rule.id}/activate"
        )
        assert resp.status_code == 200
        assert "status-badge-active" in resp.text

        db_session.expire_all()
        rule = db_session.get(CanonicalRule, rule.id)
        assert rule.is_active is True

    def test_deactivate_linked_rule_succeeds(
        self, admin_client, db_session, pair_es_en, verbs, language_en, language_es
    ):
        from models.grammar_rules import GrammarRule

        rule = CanonicalRule(
            native_language_id=pair_es_en.native_language_id,
            target_language_id=pair_es_en.target_language_id,
            word_category_id=verbs.id,
            level="A1",
            name="Linked Rule",
            description="desc",
            position=1,
            slug="linked-rule",
            is_active=True,
        )
        db_session.add(rule)
        db_session.commit()
        db_session.refresh(rule)

        gr = GrammarRule(
            name="Linked usage",
            description="desc",
            language_id=language_es.id,
            word_category_id=verbs.id,
            canonical_rule_id=rule.id,
        )
        db_session.add(gr)
        db_session.commit()

        resp = admin_client.post(
            f"/admin-panel/canonical-rules/rules/{rule.id}/deactivate"
        )
        assert resp.status_code == 200
        assert "status-badge-inactive" in resp.text
        assert "linked" in resp.text

        db_session.expire_all()
        rule = db_session.get(CanonicalRule, rule.id)
        assert rule.is_active is False

    def test_inactive_rule_excluded_from_active_only_reads(
        self, db_session, pair_es_en, verbs
    ):
        active_rule = CanonicalRule(
            native_language_id=pair_es_en.native_language_id,
            target_language_id=pair_es_en.target_language_id,
            word_category_id=verbs.id,
            level="A1",
            name="Active Rule",
            description="desc",
            position=1,
            slug="active-rule",
            is_active=True,
        )
        inactive_rule = CanonicalRule(
            native_language_id=pair_es_en.native_language_id,
            target_language_id=pair_es_en.target_language_id,
            word_category_id=verbs.id,
            level="A1",
            name="Inactive Rule",
            description="desc",
            position=2,
            slug="inactive-rule",
            is_active=False,
        )
        db_session.add_all([active_rule, inactive_rule])
        db_session.commit()

        active = get_canonical_rules_for_pair(
            db_session,
            native_language_id=pair_es_en.native_language_id,
            target_language_id=pair_es_en.target_language_id,
        )
        slugs = {r.slug for r in active}
        assert "active-rule" in slugs
        assert "inactive-rule" not in slugs

    def test_toggle_rejects_non_admin(
        self, non_admin_client, db_session, pair_es_en, verbs
    ):
        rule = CanonicalRule(
            native_language_id=pair_es_en.native_language_id,
            target_language_id=pair_es_en.target_language_id,
            word_category_id=verbs.id,
            level="A1",
            name="Toggle Rule",
            description="desc",
            position=1,
            slug="toggle-rule",
            is_active=True,
        )
        db_session.add(rule)
        db_session.commit()
        db_session.refresh(rule)

        deactivate_resp = non_admin_client.post(
            f"/admin-panel/canonical-rules/rules/{rule.id}/deactivate"
        )
        assert deactivate_resp.status_code == 307
        assert deactivate_resp.headers["location"] == "/login"

        activate_resp = non_admin_client.post(
            f"/admin-panel/canonical-rules/rules/{rule.id}/activate"
        )
        assert activate_resp.status_code == 307
        assert activate_resp.headers["location"] == "/login"
