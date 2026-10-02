import uuid
from unittest.mock import patch

import pytest

from models.canonical_rules import CanonicalRule
from models.grammar_rules import GrammarRule
from models.language import Language
from graphs.models import DuplicateCheckResult, DuplicateJudgeResult, ExistingRule
from crud.rule_similarity import get_similar_rule_candidates, check_similar_rules


def _add_language(db_session, code, name):
    lang = Language(code=code, name=name)
    db_session.add(lang)
    db_session.commit()
    db_session.refresh(lang)
    return lang


def _add_rule(db_session, language_en, target_lang, word_category, *, name, catalog_name, slug):
    canon = CanonicalRule(
        native_language_id=language_en.id,
        target_language_id=target_lang.id,
        word_category_id=word_category.id,
        level="B1",
        name=catalog_name,
        description=f"Catalog description for {slug}",
        position=1,
        slug=slug,
        is_active=True,
    )
    db_session.add(canon)
    db_session.flush()
    rule = GrammarRule(
        name=name,
        description=f"Existing rule description for {slug}",
        language_id=target_lang.id,
        word_category_id=word_category.id,
        canonical_rule_id=canon.id,
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule, canon


def _add_renamed_estar_rule(db_session, language_en, target_lang, word_category):
    return _add_rule(
        db_session, language_en, target_lang, word_category,
        name="Usage of estar",
        catalog_name="Present tense regular -ar conjugation",
        slug="present-tense-ar-conjugation",
    )[0]


class TestGetSimilarRuleCandidates:
    def test_returns_names_close_to_the_proposed_name(
        self, db_session, language_en, language_es, word_category
    ):
        match = _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
        )[0]
        unrelated = _add_rule(
            db_session, language_en, language_es, word_category,
            name="the cat sat on the mat",
            catalog_name="Nonsense",
            slug="nonsense",
        )[0]

        result = get_similar_rule_candidates(
            db_session, target_language_id=language_es.id, name="present tense ar verbs"
        )

        returned_ids = [candidate.id for candidate in result]
        assert match.id in returned_ids
        assert unrelated.id not in returned_ids

    def test_no_candidates_when_nothing_is_similar(self, db_session, language_en, language_es, word_category):
        _add_rule(
            db_session, language_en, language_es, word_category,
            name="the cat sat on the mat",
            catalog_name="Nonsense",
            slug="nonsense",
        )

        result = get_similar_rule_candidates(
            db_session, target_language_id=language_es.id, name="present tense ar verbs"
        )

        assert result == []

    def test_scopes_candidates_to_the_target_language(self, db_session, language_en, language_es, word_category):
        es_match = _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar-es",
        )[0]
        language_fr = _add_language(db_session, "fr", "French")
        _add_rule(
            db_session, language_en, language_fr, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar-fr",
        )

        result = get_similar_rule_candidates(
            db_session, target_language_id=language_es.id, name="present tense ar verbs"
        )

        assert [candidate.id for candidate in result] == [es_match.id]

    def test_normalizes_case_and_punctuation_in_the_proposed_name(
        self, db_session, language_en, language_es, word_category
    ):
        match = _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
        )[0]

        result = get_similar_rule_candidates(
            db_session,
            target_language_id=language_es.id,
            name="  Present Tense   - AR verbs! ",
        )

        assert [candidate.id for candidate in result] == [match.id]

    def test_finds_a_duplicate_renamed_to_share_only_a_suffix_word(
        self, db_session, language_en, language_es, word_category
    ):
        match = _add_renamed_estar_rule(db_session, language_en, language_es, word_category)

        result = get_similar_rule_candidates(
            db_session, target_language_id=language_es.id, name="Ser vs. estar"
        )

        assert [candidate.id for candidate in result] == [match.id]

    def test_weak_overlap_is_offered_to_the_judge_rather_than_filtered(
        self, db_session, language_en, language_es, word_category
    ):
        weak_overlap_rule = _add_rule(
            db_session, language_en, language_es, word_category,
            name="preterite imperfect tense",
            catalog_name="Preterite and Imperfect",
            slug="preterite-imperfect",
        )[0]

        result = get_similar_rule_candidates(
            db_session, target_language_id=language_es.id, name="present tense ar verbs"
        )

        assert [candidate.id for candidate in result] == [weak_overlap_rule.id]

    def test_candidate_just_below_the_threshold_is_filtered_out(
        self, db_session, language_en, language_es, word_category
    ):
        # The same rule the test above keeps scores 0.195652 against this other
        # proposed name, a hair under the 0.20 threshold. Both values are
        # pinned in test_pg_trgm.py, so the threshold itself is pinned too.
        filtered_rule = _add_rule(
            db_session, language_en, language_es, word_category,
            name="preterite imperfect tense",
            catalog_name="Preterite and Imperfect",
            slug="preterite-imperfect",
        )[0]

        result = get_similar_rule_candidates(
            db_session,
            target_language_id=language_es.id,
            name="present tense ar conjugation",
        )

        assert filtered_rule.id not in [candidate.id for candidate in result]

    def test_returns_up_to_five_candidates_ordered_by_similarity(
        self, db_session, language_en, language_es, word_category
    ):
        names = [
            "present subjunctive mood",
            "present tense ar conjugation",
            "preterite tense ar",
            "past tense ar verbs",
            "present tense",
            "present tense er verbs",
        ]
        for index, name in enumerate(names):
            _add_rule(
                db_session, language_en, language_es, word_category,
                name=name,
                catalog_name=f"Catalog {name}",
                slug=f"rule-{index}",
            )

        result = get_similar_rule_candidates(
            db_session, target_language_id=language_es.id, name="present tense ar verbs"
        )

        # pg_trgm scores these against "present tense ar verbs" as 0.7692,
        # 0.6087, 0.5926, 0.4857, 0.4000 and 0.2000, so all six clear the 0.20
        # threshold and the sixth is dropped by MAX_CANDIDATES. These values are
        # pinned in test_pg_trgm.py.
        assert [candidate.name for candidate in result] == [
            "present tense er verbs",
            "present tense",
            "past tense ar verbs",
            "present tense ar conjugation",
            "preterite tense ar",
        ]

    def test_each_candidate_carries_its_catalog_entry_name(
        self, db_session, language_en, language_es, word_category
    ):
        _, canon = _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
        )

        result = get_similar_rule_candidates(
            db_session, target_language_id=language_es.id, name="present tense ar verbs"
        )

        assert result[0].catalog_name == canon.name

class TestCheckSimilarRules:
    @patch("crud.rule_similarity.judge_chain")
    def test_duplicate_renamed_to_share_only_a_suffix_word_reaches_the_judge(
        self, mock_judge, db_session, language_en, language_es, word_category
    ):
        rule = _add_renamed_estar_rule(db_session, language_en, language_es, word_category)
        mock_judge.invoke.return_value = DuplicateJudgeResult(
            similar=True, best_match_id=rule.id
        )

        result = check_similar_rules(
            db_session,
            target_language_id=language_es.id,
            proposed_title="Ser vs. estar",
            proposed_description="Distinguish ser from estar.",
        )

        mock_judge.invoke.assert_called_once()
        assert result.similar is True
        assert result.existing_rule is not None
        assert result.existing_rule.name == "Usage of estar"

    @patch("crud.rule_similarity.judge_chain")
    def test_no_similar_candidates_returns_not_similar_without_judging(
        self, mock_judge, db_session, language_en, language_es, word_category
    ):
        _add_rule(
            db_session, language_en, language_es, word_category,
            name="the cat sat on the mat",
            catalog_name="Nonsense",
            slug="nonsense",
        )

        result = check_similar_rules(
            db_session,
            target_language_id=language_es.id,
            proposed_title="present tense ar verbs",
            proposed_description="Conjugate -ar verbs in the present tense.",
        )

        assert result is not None
        assert result.similar is False
        assert result.existing_rule is None
        mock_judge.invoke.assert_not_called()

    @patch("crud.rule_similarity.judge_chain")
    def test_judge_match_returns_the_existing_rule(
        self, mock_judge, db_session, language_en, language_es, word_category
    ):
        rule = _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
        )[0]
        mock_judge.invoke.return_value = DuplicateJudgeResult(
            similar=True, best_match_id=rule.id
        )

        result = check_similar_rules(
            db_session,
            target_language_id=language_es.id,
            proposed_title="present tense ar verbs",
            proposed_description="Conjugate -ar verbs in the present tense.",
        )

        assert result.similar is True
        assert result.existing_rule is not None
        assert result.existing_rule.id == rule.id
        assert result.existing_rule.name == rule.name
        assert result.existing_rule.description == rule.description

    @patch("crud.rule_similarity.judge_chain")
    def test_judge_selecting_no_match_returns_not_similar(
        self, mock_judge, db_session, language_en, language_es, word_category
    ):
        _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
        )[0]
        mock_judge.invoke.return_value = DuplicateJudgeResult(
            similar=False, best_match_id=None
        )

        result = check_similar_rules(
            db_session,
            target_language_id=language_es.id,
            proposed_title="present tense ar verbs",
            proposed_description="Conjugate -ar verbs in the present tense.",
        )

        assert result.similar is False
        assert result.existing_rule is None

    @patch("crud.rule_similarity.judge_chain")
    def test_judge_id_outside_the_candidate_set_is_rejected(
        self, mock_judge, db_session, language_en, language_es, word_category
    ):
        _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
        )[0]
        mock_judge.invoke.return_value = DuplicateJudgeResult(
            similar=True, best_match_id=uuid.uuid4()
        )

        result = check_similar_rules(
            db_session,
            target_language_id=language_es.id,
            proposed_title="present tense ar verbs",
            proposed_description="Conjugate -ar verbs in the present tense.",
        )

        assert result.similar is False
        assert result.existing_rule is None

    @patch("crud.rule_similarity.judge_chain")
    def test_judge_receives_the_proposal_and_each_catalog_entry_name(
        self, mock_judge, db_session, language_en, language_es, word_category
    ):
        rule, canon = _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
        )
        mock_judge.invoke.return_value = DuplicateJudgeResult(
            similar=False, best_match_id=None
        )

        check_similar_rules(
            db_session,
            target_language_id=language_es.id,
            proposed_title="present tense ar verbs",
            proposed_description="Conjugate -ar verbs in the present tense.",
        )

        prompt_inputs = mock_judge.invoke.call_args[0][0]
        assert prompt_inputs["rule_title"] == "present tense ar verbs"
        assert prompt_inputs["rule_explanation"] == (
            "Conjugate -ar verbs in the present tense."
        )
        assert str(rule.id) in prompt_inputs["candidates"]
        assert rule.name in prompt_inputs["candidates"]
        assert canon.name in prompt_inputs["candidates"]
        assert rule.description in prompt_inputs["candidates"]

    @patch("crud.rule_similarity.judge_chain")
    def test_check_persists_no_rows(
        self, mock_judge, db_session, language_en, language_es, word_category
    ):
        rule = _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
        )[0]
        mock_judge.invoke.return_value = DuplicateJudgeResult(
            similar=True, best_match_id=rule.id
        )
        rules_before = db_session.query(GrammarRule).count()
        catalogs_before = db_session.query(CanonicalRule).count()
        new_object_count_before = len(db_session.new)

        check_similar_rules(
            db_session,
            target_language_id=language_es.id,
            proposed_title="present tense ar verbs",
            proposed_description="Conjugate -ar verbs in the present tense.",
        )

        assert db_session.query(GrammarRule).count() == rules_before
        assert db_session.query(CanonicalRule).count() == catalogs_before
        assert len(db_session.new) == new_object_count_before
