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
from crud.rules import create_grammar_rule
from tests.catalog_text import (
    PRESENT_TENSE_ER_DESCRIPTION,
    PRESENT_TENSE_ER_NAME,
    PRESENT_TENSE_IR_DESCRIPTION,
    PRESENT_TENSE_IR_NAME,
    REFLEXIVE_VERBS_DESCRIPTION,
    REFLEXIVE_VERBS_NAME,
    SER_VS_ESTAR_DESCRIPTION,
    SER_VS_ESTAR_NAME,
)

# Rule text as the rule-creation flow produced it, not catalog text, so it has no
# file to stay in step with and is kept inline.
ESTAR_RULE_NAME = "Usage of verb estar"
ESTAR_RULE_DESCRIPTION = (
    'Estar is one of two Spanish verbs that mean "to be", used primarily to '
    "describe temporary states, conditions, emotions, and locations."
)
SER_RULE_NAME = "Usage of verb ser"
SER_RULE_DESCRIPTION = (
    'The Spanish verb ser means "to be" and is used to describe permanent or '
    "core traits, identity, and facts."
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

    def test_excludes_entry_linked_to_several_faithful_copies(
        self, db_session, language_en, language_es, word_category, canonical_rule, grammar_rule
    ):
        """Several rules on one entry are fine when each teaches that entry.

        The count is not what retires the entry — a faithful copy is. Both rules
        here are named after "Noun Gender", the second at 0.5455, so the entry is
        genuinely covered. Whether it takes one rule or several is irrelevant
        either way, which is the point #44 made about the relation.
        """
        create_grammar_rule(
            db=db_session,
            title="Noun Gender, in detail",
            description="The same contrast, at greater length.",
            language_id=language_es.id,
            word_category_id=word_category.id,
            canonical_rule_id=canonical_rule.id,
        )
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

    def test_suggests_entry_whose_linked_rules_are_different_rules(
        self, db_session, language_en, language_es, word_category
    ):
        entry = upsert_canonical_rule(
            db_session,
            native_language_id=language_en.id,
            target_language_id=language_es.id,
            word_category_id=word_category.id,
            slug="ser-vs-estar",
            level="A1",
            name=SER_VS_ESTAR_NAME,
            description=SER_VS_ESTAR_DESCRIPTION,
            position=1,
        )
        for title in ["Usage of verb estar", "Usage of verb ser"]:
            create_grammar_rule(
                db=db_session,
                title=title,
                description="A description of its own.",
                language_id=language_es.id,
                word_category_id=word_category.id,
                canonical_rule_id=entry.id,
            )

        rules = get_missing_canonical_rules_for_pair(
            db_session, language_en.id, language_es.id
        )

        assert [r.slug for r in rules] == ["ser-vs-estar"]

    def test_excludes_entry_linked_to_a_lightly_reworded_copy(
        self, db_session, language_en, language_es, word_category
    ):
        """The narrow edge of the coverage window.

        "Ser and estar: which to use" scores 0.3333 against "Ser vs. estar" — the
        least a faithful copy can score and still count — while a sub-rule like
        "Usage of verb estar" scores 0.2692 and must not. That 0.0641 margin is
        the whole tolerance this rule has, so pin both sides of it here rather
        than leaving them to a similarity value nobody reads.
        """
        entry = upsert_canonical_rule(
            db_session,
            native_language_id=language_en.id,
            target_language_id=language_es.id,
            word_category_id=word_category.id,
            slug="ser-vs-estar",
            level="A1",
            name=SER_VS_ESTAR_NAME,
            description=SER_VS_ESTAR_DESCRIPTION,
            position=1,
        )
        create_grammar_rule(
            db=db_session,
            title="Ser and estar: which to use",
            description="A description of its own.",
            language_id=language_es.id,
            word_category_id=word_category.id,
            canonical_rule_id=entry.id,
        )

        rules = get_missing_canonical_rules_for_pair(
            db_session, language_en.id, language_es.id
        )

        assert [r.slug for r in rules] == []

    @pytest.mark.parametrize(
        "slug,entry_name,entry_description,linked_rule_name,linked_rule_description",
        [
            (
                "present-tense-er-conjugation",
                PRESENT_TENSE_ER_NAME,
                PRESENT_TENSE_ER_DESCRIPTION,
                ESTAR_RULE_NAME,
                ESTAR_RULE_DESCRIPTION,
            ),
            (
                "present-tense-ir-conjugation",
                PRESENT_TENSE_IR_NAME,
                PRESENT_TENSE_IR_DESCRIPTION,
                ESTAR_RULE_NAME,
                ESTAR_RULE_DESCRIPTION,
            ),
            (
                "reflexive-verbs",
                REFLEXIVE_VERBS_NAME,
                REFLEXIVE_VERBS_DESCRIPTION,
                SER_RULE_NAME,
                SER_RULE_DESCRIPTION,
            ),
        ],
    )
    def test_description_overlap_alone_does_not_count_as_coverage(
        self,
        db_session,
        language_en,
        language_es,
        word_category,
        slug,
        entry_name,
        entry_description,
        linked_rule_name,
        linked_rule_description,
    ):
        """A rule that shares vocabulary with an entry teaches a different rule.

        Each pair here scores above the 0.20 retrieval threshold on description
        alone — 0.2331, 0.2134 and 0.2473 — while the names score 0.0364, 0.0179
        and 0.1333. Comparing description as well as name would retire all three
        entries on nothing but overlap between two descriptions of Spanish verbs,
        which is the false positive #47 exists to remove. The rule names and
        descriptions come from the rule-creation flow rather than the catalog, so
        they are inline here with no file to keep in step.
        """
        entry = upsert_canonical_rule(
            db_session,
            native_language_id=language_en.id,
            target_language_id=language_es.id,
            word_category_id=word_category.id,
            slug=slug,
            level="A2",
            name=entry_name,
            description=entry_description,
            position=1,
        )
        create_grammar_rule(
            db=db_session,
            title=linked_rule_name,
            description=linked_rule_description,
            language_id=language_es.id,
            word_category_id=word_category.id,
            canonical_rule_id=entry.id,
        )

        rules = get_missing_canonical_rules_for_pair(
            db_session, language_en.id, language_es.id
        )

        assert [r.slug for r in rules] == [entry.slug]

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