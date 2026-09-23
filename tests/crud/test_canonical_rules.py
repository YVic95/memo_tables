import uuid

import pytest
from sqlalchemy import func

from models.canonical_rules import CanonicalRule
from models.grammar_rules import GrammarRule
from models.language import Language
from models.word_categories import WordCategory
from crud.canonical_rules import (
    deactivate_canonical_rules_not_in,
    get_canonical_rule_by_id,
    get_canonical_rules_for_pair,
    get_missing_canonical_rules_for_pair,
    upsert_canonical_rule,
)


@pytest.fixture()
def verb_category(db_session):
    category = WordCategory(name="Verbs", slug="verb")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


def _populate(
    db_session,
    language_en,
    language_es,
    verb_category,
    entries,
):
    for entry in entries:
        upsert_canonical_rule(
            db_session,
            native_language_id=language_en.id,
            target_language_id=language_es.id,
            word_category_id=verb_category.id,
            slug=entry["slug"],
            level=entry["level"],
            name=entry["name"],
            description=entry["description"],
            position=entry["position"],
        )


def _count_rules(db_session):
    return db_session.query(func.count(CanonicalRule.id)).scalar()


class TestGetCanonicalRulesForPair:
    def test_returns_active_entries_ordered_by_level_then_position(
        self, db_session, language_en, language_es, verb_category
    ):
        _populate(
            db_session,
            language_en,
            language_es,
            verb_category,
            [
                {"slug": "a2-b", "level": "A2", "name": "A2 B", "description": "d", "position": 2},
                {"slug": "a1-c", "level": "A1", "name": "A1 C", "description": "d", "position": 3},
                {"slug": "a1-a", "level": "A1", "name": "A1 A", "description": "d", "position": 1},
                {"slug": "b1-a", "level": "B1", "name": "B1 A", "description": "d", "position": 1},
            ],
        )

        rules = get_canonical_rules_for_pair(db_session, language_en.id, language_es.id)

        assert [r.slug for r in rules] == ["a1-a", "a1-c", "a2-b", "b1-a"]

    def test_excludes_deactivated_entries(
        self, db_session, language_en, language_es, verb_category
    ):
        _populate(
            db_session,
            language_en,
            language_es,
            verb_category,
            [
                {"slug": "active-rule", "level": "A1", "name": "Active", "description": "d", "position": 1},
                {"slug": "retired-rule", "level": "A1", "name": "Retired", "description": "d", "position": 2},
            ],
        )
        deactivate_canonical_rules_not_in(db_session, language_en.id, language_es.id, {"active-rule"})

        rules = get_canonical_rules_for_pair(db_session, language_en.id, language_es.id)

        assert [r.slug for r in rules] == ["active-rule"]

    def test_is_scoped_to_the_language_pair(
        self, db_session, language_en, language_es, verb_category
    ):
        other_native = Language(code="de", name="German")
        db_session.add(other_native)
        db_session.commit()
        db_session.refresh(other_native)

        _populate(
            db_session,
            language_en,
            language_es,
            verb_category,
            [{"slug": "shared-slug", "level": "A1", "name": "Shared", "description": "d", "position": 1}],
        )
        upsert_canonical_rule(
            db_session,
            native_language_id=other_native.id,
            target_language_id=language_es.id,
            word_category_id=verb_category.id,
            slug="shared-slug",
            level="A1",
            name="Shared",
            description="d",
            position=1,
        )

        en_es_rules = get_canonical_rules_for_pair(db_session, language_en.id, language_es.id)
        de_es_rules = get_canonical_rules_for_pair(db_session, other_native.id, language_es.id)

        assert len(en_es_rules) == 1
        assert len(de_es_rules) == 1
        assert en_es_rules[0].id != de_es_rules[0].id


class TestGetCanonicalRuleById:
    def test_returns_the_catalog_entry_for_a_known_id(
        self, db_session, canonical_rule
    ):
        rule = get_canonical_rule_by_id(db_session, canonical_rule.id)

        assert rule is not None
        assert rule.id == canonical_rule.id
        assert rule.word_category_id == canonical_rule.word_category_id

    def test_returns_none_for_an_unknown_id(self, db_session):
        assert get_canonical_rule_by_id(db_session, uuid.uuid4()) is None


class TestGetMissingCanonicalRulesForPair:
    def test_returns_active_entry_with_no_linked_rule(
        self, db_session, language_en, language_es, word_category
    ):
        upsert_canonical_rule(
            db_session,
            native_language_id=language_en.id,
            target_language_id=language_es.id,
            word_category_id=word_category.id,
            slug="missing-rule",
            level="A1",
            name="Missing Rule",
            description="d",
            position=1,
        )

        rules = get_missing_canonical_rules_for_pair(
            db_session, language_en.id, language_es.id
        )

        assert [r.slug for r in rules] == ["missing-rule"]

    def test_excludes_entry_linked_to_a_persisted_rule(
        self, db_session, language_en, language_es, word_category, canonical_rule, grammar_rule
    ):
        upsert_canonical_rule(
            db_session,
            native_language_id=language_en.id,
            target_language_id=language_es.id,
            word_category_id=word_category.id,
            slug="still-missing",
            level="A1",
            name="Still Missing",
            description="d",
            position=2,
        )

        rules = get_missing_canonical_rules_for_pair(
            db_session, language_en.id, language_es.id
        )

        assert [r.slug for r in rules] == ["still-missing"]

    def test_excludes_deactivated_entries(
        self, db_session, language_en, language_es, verb_category
    ):
        _populate(
            db_session,
            language_en,
            language_es,
            verb_category,
            [
                {"slug": "active-missing", "level": "A1", "name": "Active", "description": "d", "position": 1},
                {"slug": "retired", "level": "A1", "name": "Retired", "description": "d", "position": 2},
            ],
        )
        deactivate_canonical_rules_not_in(db_session, language_en.id, language_es.id, {"active-missing"})

        rules = get_missing_canonical_rules_for_pair(
            db_session, language_en.id, language_es.id
        )

        assert [r.slug for r in rules] == ["active-missing"]

    def test_orders_by_level_then_position(
        self, db_session, language_en, language_es, verb_category
    ):
        _populate(
            db_session,
            language_en,
            language_es,
            verb_category,
            [
                {"slug": "a2-b", "level": "A2", "name": "A2 B", "description": "d", "position": 2},
                {"slug": "a1-c", "level": "A1", "name": "A1 C", "description": "d", "position": 3},
                {"slug": "a1-a", "level": "A1", "name": "A1 A", "description": "d", "position": 1},
                {"slug": "b1-a", "level": "B1", "name": "B1 A", "description": "d", "position": 1},
            ],
        )

        rules = get_missing_canonical_rules_for_pair(
            db_session, language_en.id, language_es.id
        )

        assert [r.slug for r in rules] == ["a1-a", "a1-c", "a2-b", "b1-a"]

    def test_is_scoped_to_the_language_pair(
        self, db_session, language_en, language_es, word_category
    ):
        other_native = Language(code="de", name="German")
        db_session.add(other_native)
        db_session.commit()
        db_session.refresh(other_native)
        upsert_canonical_rule(
            db_session,
            native_language_id=language_en.id,
            target_language_id=language_es.id,
            word_category_id=word_category.id,
            slug="en-es-rule",
            level="A1",
            name="En-Es",
            description="d",
            position=1,
        )
        upsert_canonical_rule(
            db_session,
            native_language_id=other_native.id,
            target_language_id=language_es.id,
            word_category_id=word_category.id,
            slug="de-es-rule",
            level="A1",
            name="De-Es",
            description="d",
            position=1,
        )

        rules = get_missing_canonical_rules_for_pair(
            db_session, language_en.id, language_es.id
        )

        assert [r.slug for r in rules] == ["en-es-rule"]


class TestUpsertCanonicalRule:
    def test_creates_new_rule(self, db_session, language_en, language_es, verb_category):
        rule = upsert_canonical_rule(
            db_session,
            native_language_id=language_en.id,
            target_language_id=language_es.id,
            word_category_id=verb_category.id,
            slug="present-tense-ar",
            level="A1",
            name="Present tense regular -ar conjugation",
            description="Conjugate -ar verbs.",
            position=1,
        )

        assert rule.is_active is True
        assert _count_rules(db_session) == 1

    def test_updates_existing_rule_by_pair_and_slug_without_duplicating(
        self, db_session, language_en, language_es, verb_category
    ):
        upsert_canonical_rule(
            db_session,
            native_language_id=language_en.id,
            target_language_id=language_es.id,
            word_category_id=verb_category.id,
            slug="present-tense-ar",
            level="A1",
            name="Original name",
            description="Original description",
            position=1,
        )
        upsert_canonical_rule(
            db_session,
            native_language_id=language_en.id,
            target_language_id=language_es.id,
            word_category_id=verb_category.id,
            slug="present-tense-ar",
            level="A2",
            name="Updated name",
            description="Updated description",
            position=2,
        )

        rule = db_session.query(CanonicalRule).filter(CanonicalRule.slug == "present-tense-ar").one()
        assert rule.name == "Updated name"
        assert rule.description == "Updated description"
        assert rule.level == "A2"
        assert rule.position == 2
        assert _count_rules(db_session) == 1

    def test_upsert_reactivates_a_deactivated_rule(
        self, db_session, language_en, language_es, verb_category
    ):
        rule = upsert_canonical_rule(
            db_session,
            native_language_id=language_en.id,
            target_language_id=language_es.id,
            word_category_id=verb_category.id,
            slug="comeback-rule",
            level="A2",
            name="Comeback",
            description="d",
            position=1,
        )
        deactivate_canonical_rules_not_in(db_session, language_en.id, language_es.id, set())

        rule = upsert_canonical_rule(
            db_session,
            native_language_id=language_en.id,
            target_language_id=language_es.id,
            word_category_id=verb_category.id,
            slug="comeback-rule",
            level="A2",
            name="Comeback",
            description="d",
            position=1,
        )

        assert rule.is_active is True


class TestDeactivateCanonicalRulesNotIn:
    def test_deactivates_active_rules_absent_from_slugs_but_keeps_rows(
        self, db_session, language_en, language_es, verb_category
    ):
        _populate(
            db_session,
            language_en,
            language_es,
            verb_category,
            [
                {"slug": "keep-rule", "level": "A1", "name": "Keep", "description": "d", "position": 1},
                {"slug": "drop-rule", "level": "A1", "name": "Drop", "description": "d", "position": 2},
            ],
        )

        deactivate_canonical_rules_not_in(db_session, language_en.id, language_es.id, {"keep-rule"})

        assert db_session.query(CanonicalRule).filter(CanonicalRule.slug == "drop-rule").one().is_active is False
        assert db_session.query(CanonicalRule).filter(CanonicalRule.slug == "keep-rule").one().is_active is True
        assert _count_rules(db_session) == 2

    def test_does_not_touch_rules_of_another_pair(
        self, db_session, language_en, language_es, verb_category
    ):
        other_native = Language(code="de", name="German")
        db_session.add(other_native)
        db_session.commit()
        db_session.refresh(other_native)
        _populate(
            db_session,
            language_en,
            language_es,
            verb_category,
            [{"slug": "en-rule", "level": "A1", "name": "En", "description": "d", "position": 1}],
        )
        upsert_canonical_rule(
            db_session,
            native_language_id=other_native.id,
            target_language_id=language_es.id,
            word_category_id=verb_category.id,
            slug="de-rule",
            level="A1",
            name="De",
            description="d",
            position=1,
        )

        deactivate_canonical_rules_not_in(db_session, language_en.id, language_es.id, set())

        assert db_session.query(CanonicalRule).filter(CanonicalRule.slug == "de-rule").one().is_active is True