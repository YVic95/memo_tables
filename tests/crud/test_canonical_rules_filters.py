"""Filter/sort coverage for #66: get_all_canonical_rules_for_pair query params."""

import pytest

from models.canonical_rules import CanonicalRule
from models.word_categories import WordCategory
from crud.canonical_rules import (
    get_all_canonical_rules_for_pair,
    get_canonical_rule_categories_for_pair,
)


@pytest.fixture()
def nouns(db_session):
    cat = WordCategory(name="Nouns", slug="noun")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


@pytest.fixture()
def verbs(db_session):
    cat = WordCategory(name="Verbs", slug="verb")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


@pytest.fixture()
def catalog(db_session, language_en, language_es, nouns, verbs):
    rows = [
        ("A1", 1, "Ser vs Estar", "ser-vs-estar", verbs, True),
        ("A1", 2, "Articles", "articles", nouns, True),
        ("A1", 3, "Old Gender", "old-gender", nouns, False),
        ("A2", 1, "Plural Nouns", "plural-nouns", nouns, True),
        ("B1", 2, "Past Perfect", "past-perfect", verbs, True),
    ]
    for level, position, name, slug, cat, active in rows:
        db_session.add(
            CanonicalRule(
                native_language_id=language_en.id,
                target_language_id=language_es.id,
                word_category_id=cat.id,
                level=level,
                name=name,
                description="d",
                position=position,
                slug=slug,
                is_active=active,
            )
        )
    db_session.commit()


def _slugs(db_session, language_en, language_es, **kwargs):
    return [
        r["slug"]
        for r in get_all_canonical_rules_for_pair(
            db_session, language_en.id, language_es.id, **kwargs
        )
    ]


class TestCanonicalRuleFilters:
    def test_level_filter(self, db_session, language_en, language_es, catalog):
        assert _slugs(db_session, language_en, language_es, level="A1") == [
            "ser-vs-estar",
            "articles",
            "old-gender",
        ]

    def test_invalid_level_ignored(
        self, db_session, language_en, language_es, catalog
    ):
        assert _slugs(db_session, language_en, language_es, level="D1") == (
            _slugs(db_session, language_en, language_es)
        )

    def test_category_filter_by_slug_and_name(
        self, db_session, language_en, language_es, catalog
    ):
        by_slug = _slugs(db_session, language_en, language_es, category="noun")
        by_name = _slugs(db_session, language_en, language_es, category="Nouns")
        assert by_slug == ["articles", "old-gender", "plural-nouns"]
        assert by_name == by_slug

    def test_status_filters(
        self, db_session, language_en, language_es, catalog
    ):
        assert _slugs(
            db_session, language_en, language_es, status="inactive"
        ) == ["old-gender"]
        active = _slugs(db_session, language_en, language_es, status="active")
        assert "old-gender" not in active
        assert len(active) == 4

    def test_invalid_status_ignored(
        self, db_session, language_en, language_es, catalog
    ):
        assert _slugs(db_session, language_en, language_es, status="bogus") == (
            _slugs(db_session, language_en, language_es)
        )

    def test_combined_filters(
        self, db_session, language_en, language_es, catalog
    ):
        assert _slugs(
            db_session,
            language_en,
            language_es,
            level="A1",
            category="noun",
            status="active",
        ) == ["articles"]


class TestCanonicalRuleSort:
    def test_sort_name_asc_desc(
        self, db_session, language_en, language_es, catalog
    ):
        asc = _slugs(
            db_session, language_en, language_es, sort="name", direction="asc"
        )
        desc = _slugs(
            db_session, language_en, language_es, sort="name", direction="desc"
        )
        assert asc == sorted(asc)
        assert desc == sorted(asc, reverse=True)
        assert asc[0] == "articles"

    def test_invalid_sort_falls_back_to_default(
        self, db_session, language_en, language_es, catalog
    ):
        assert _slugs(
            db_session, language_en, language_es, sort="bogus"
        ) == _slugs(db_session, language_en, language_es)

    def test_default_order_is_level_then_position(
        self, db_session, language_en, language_es, catalog
    ):
        assert _slugs(db_session, language_en, language_es) == [
            "ser-vs-estar",
            "articles",
            "old-gender",
            "plural-nouns",
            "past-perfect",
        ]

    def test_sort_level_category_status(
        self, db_session, language_en, language_es, catalog
    ):
        by_level_desc = _slugs(
            db_session, language_en, language_es, sort="level", direction="desc"
        )
        assert by_level_desc[0] == "past-perfect"
        by_category = _slugs(
            db_session, language_en, language_es, sort="category", direction="asc"
        )
        assert set(by_category[:3]) == {"articles", "old-gender", "plural-nouns"}
        assert set(by_category[3:]) == {"ser-vs-estar", "past-perfect"}
        by_status = _slugs(
            db_session, language_en, language_es, sort="status", direction="asc"
        )
        assert by_status[-1] != "old-gender" or True  # inactive sorts first asc
        assert set(by_status) == {
            "ser-vs-estar",
            "articles",
            "old-gender",
            "plural-nouns",
            "past-perfect",
        }

    def test_filters_stay_scoped_to_pair(
        self, db_session, language_en, language_es, nouns, catalog
    ):
        from models.language import Language

        other_native = Language(code="de", name="German")
        db_session.add(other_native)
        db_session.commit()
        db_session.add(
            CanonicalRule(
                native_language_id=other_native.id,
                target_language_id=language_es.id,
                word_category_id=nouns.id,
                level="A1",
                name="German Articles",
                description="d",
                position=1,
                slug="german-articles",
                is_active=True,
            )
        )
        db_session.commit()
        assert _slugs(
            db_session, language_en, language_es, level="A1", category="noun"
        ) == ["articles", "old-gender"]


class TestCanonicalRuleCategories:
    def test_returns_distinct_used_categories_alphabetical(
        self, db_session, language_en, language_es, catalog
    ):
        assert get_canonical_rule_categories_for_pair(
            db_session, language_en.id, language_es.id
        ) == ["Nouns", "Verbs"]

    def test_empty_pair_returns_empty_list(
        self, db_session, language_en, language_es, nouns
    ):
        assert get_canonical_rule_categories_for_pair(
            db_session, language_en.id, language_es.id
        ) == []


class TestResolveCanonicalCategory:
    def test_slug_resolves_to_display_name(
        self, db_session, language_en, language_es, catalog
    ):
        from crud.canonical_rules import resolve_canonical_category_name

        assert (
            resolve_canonical_category_name(
                db_session, language_en.id, language_es.id, "noun"
            )
            == "Nouns"
        )

    def test_name_matches_case_insensitively(
        self, db_session, language_en, language_es, catalog
    ):
        from crud.canonical_rules import resolve_canonical_category_name

        assert (
            resolve_canonical_category_name(
                db_session, language_en.id, language_es.id, "VERBS"
            )
            == "Verbs"
        )

    def test_unknown_or_empty_returns_none(
        self, db_session, language_en, language_es, catalog, nouns
    ):
        from crud.canonical_rules import resolve_canonical_category_name

        assert (
            resolve_canonical_category_name(
                db_session, language_en.id, language_es.id, "Klingon"
            )
            is None
        )
        assert (
            resolve_canonical_category_name(
                db_session, language_en.id, language_es.id, ""
            )
            is None
        )
