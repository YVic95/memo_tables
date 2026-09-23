import os

import pytest

from models.canonical_rules import CanonicalRule
from sqlalchemy import func

from scripts.load_canon import (
    CATALOGS_DIR,
    load_catalog_yaml,
    sync_catalog_from_document,
)

from tests.crud.test_canonical_rules import _count_rules

SHIPPED_EN_ES_PATH = os.path.join(CATALOGS_DIR, "en-es.yaml")


def _en_es_document():
    return {
        "native_language": "en",
        "target_language": "es",
        "rules": [
            {
                "slug": "present-tense-ar",
                "category": "verb",
                "level": "A1",
                "position": 1,
                "name": "Present tense regular -ar conjugation",
                "description": "Conjugate -ar verbs.",
            },
            {
                "slug": "reflexive-verbs",
                "category": "verb",
                "level": "A2",
                "position": 1,
                "name": "Reflexive verbs",
                "description": "Actions performed on oneself.",
            },
            {
                "slug": "present-tense-er",
                "category": "verb",
                "level": "A1",
                "position": 2,
                "name": "Present tense regular -er conjugation",
                "description": "Conjugate -er verbs.",
            },
        ],
    }


@pytest.fixture()
def verb_category(db_session):
    from models.word_categories import WordCategory

    category = WordCategory(name="Verbs", slug="verb")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


class TestSyncCatalogFromDocument:
    def test_inserts_entries_and_resolves_codes_and_slugs(
        self, db_session, language_en, language_es, verb_category
    ):
        sync_catalog_from_document(db_session, _en_es_document())

        rules = db_session.query(CanonicalRule).order_by(CanonicalRule.slug).all()
        assert len(rules) == 3
        for rule in rules:
            assert rule.native_language_id == language_en.id
            assert rule.target_language_id == language_es.id
            assert rule.word_category_id == verb_category.id
            assert rule.is_active is True

    def test_rerun_converges_without_duplicate_rows(
        self, db_session, language_en, language_es, verb_category
    ):
        sync_catalog_from_document(db_session, _en_es_document())
        sync_catalog_from_document(db_session, _en_es_document())

        assert _count_rules(db_session) == 3

    def test_entry_removed_from_file_is_deactivated_but_not_deleted(
        self, db_session, language_en, language_es, verb_category
    ):
        sync_catalog_from_document(db_session, _en_es_document())

        removed_document = {
            "native_language": "en",
            "target_language": "es",
            "rules": [
                entry
                for entry in _en_es_document()["rules"]
                if entry["slug"] != "reflexive-verbs"
            ],
        }
        sync_catalog_from_document(db_session, removed_document)

        assert _count_rules(db_session) == 3
        retired = (
            db_session.query(CanonicalRule)
            .filter(CanonicalRule.slug == "reflexive-verbs")
            .one()
        )
        assert retired.is_active is False

    def test_entry_readded_to_file_is_reactivated(
        self, db_session, language_en, language_es, verb_category
    ):
        sync_catalog_from_document(db_session, _en_es_document())
        without_reflexive = {
            "native_language": "en",
            "target_language": "es",
            "rules": [
                entry
                for entry in _en_es_document()["rules"]
                if entry["slug"] != "reflexive-verbs"
            ],
        }
        sync_catalog_from_document(db_session, without_reflexive)
        sync_catalog_from_document(db_session, _en_es_document())

        rule = (
            db_session.query(CanonicalRule)
            .filter(CanonicalRule.slug == "reflexive-verbs")
            .one()
        )
        assert rule.is_active is True

    def test_updates_existing_entry_in_place(
        self, db_session, language_en, language_es, verb_category
    ):
        initial = _en_es_document()
        sync_catalog_from_document(db_session, initial)

        changed = _en_es_document()
        changed["rules"][0]["name"] = "Renamed rule"
        changed["rules"][0]["position"] = 5
        sync_catalog_from_document(db_session, changed)

        rule = (
            db_session.query(CanonicalRule)
            .filter(CanonicalRule.slug == "present-tense-ar")
            .one()
        )
        assert rule.name == "Renamed rule"
        assert rule.position == 5
        assert _count_rules(db_session) == 3

    def test_unknown_language_code_raises(
        self, db_session, language_en, language_es, verb_category
    ):
        document = _en_es_document()
        document["target_language"] = "xx"

        with pytest.raises(ValueError, match="xx"):
            sync_catalog_from_document(db_session, document)

    def test_unknown_category_slug_raises(
        self, db_session, language_en, language_es, verb_category
    ):
        document = _en_es_document()
        document["rules"][0]["category"] = "not-a-category"

        with pytest.raises(ValueError, match="not-a-category"):
            sync_catalog_from_document(db_session, document)


class TestDefaultCatalogFile:
    def test_shipped_file_exists_and_parses(self):
        assert os.path.exists(SHIPPED_EN_ES_PATH)
        document = load_catalog_yaml(SHIPPED_EN_ES_PATH)

        assert document["native_language"] == "en"
        assert document["target_language"] == "es"
        assert len(document["rules"]) == 12
        for entry in document["rules"]:
            assert entry["category"] == "verb"
            assert entry["level"] in {"A1", "A2", "B1", "B2", "C1", "C2"}
            assert entry["name"]
            assert entry["description"]
            assert entry["position"] >= 1
            assert entry["slug"]

    def test_shipped_file_syncs_idempotently(
        self, db_session, language_en, language_es, verb_category
    ):
        document = load_catalog_yaml(SHIPPED_EN_ES_PATH)

        sync_catalog_from_document(db_session, document)
        sync_catalog_from_document(db_session, document)

        assert _count_rules(db_session) == 12

        rules = db_session.query(CanonicalRule).all()
        assert all(rule.is_active for rule in rules)