import itertools
import logging
import uuid
from unittest.mock import patch

from models.canonical_rules import CanonicalRule
from models.grammar_rules import GrammarRule
from models.language import Language
from graphs.models import DuplicateJudgeResult
from crud.rule_similarity import (
    TRIGRAM_SIMILARITY_THRESHOLD,
    _similarity_or_zero,
    check_similar_rules,
    get_similar_rule_candidates,
)
from tests.catalog_text import REFLEXIVE_VERBS_DESCRIPTION, SER_VS_ESTAR_DESCRIPTION

# How many matches the judge names. Deliberately not production's
# MAX_SIMILAR_RULES_SHOWN: the double has to be able to disagree with what
# production enforces, or a cap that regressed would be invisible here.
# test_more_than_three_matches_are_capped_here_not_only_in_the_prompt pins the gap
# by handing production five matches.
MAX_RULES_THE_JUDGE_NAMES = 3
from tests.pg_trgm import similarity


def _add_language(db_session, code, name):
    lang = Language(code=code, name=name)
    db_session.add(lang)
    db_session.commit()
    db_session.refresh(lang)
    return lang


def _add_grammar_rule(db_session, target_lang, word_category, canon, *, name, description):
    rule = GrammarRule(
        name=name,
        description=description,
        language_id=target_lang.id,
        word_category_id=word_category.id,
        canonical_rule_id=canon.id,
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule


def _add_canonical_rule(db_session, language_en, target_lang, word_category, *, name, slug):
    canon = CanonicalRule(
        native_language_id=language_en.id,
        target_language_id=target_lang.id,
        word_category_id=word_category.id,
        level="B1",
        name=name,
        description=f"Catalog description for {slug}",
        position=1,
        slug=slug,
        is_active=True,
    )
    db_session.add(canon)
    db_session.flush()
    return canon


def _add_rule(
    db_session,
    language_en,
    target_lang,
    word_category,
    *,
    name,
    catalog_name,
    slug,
    description=None,
):
    """A rule linked to its catalog entry, with filler description text by default.

    Pass `description=None` only where the description is what the test is about;
    the filler is indistinguishable between rules, so it cannot stand in for a
    real one.
    """
    canon = _add_canonical_rule(
        db_session,
        language_en,
        target_lang,
        word_category,
        name=catalog_name,
        slug=slug,
    )
    rule = _add_grammar_rule(
        db_session,
        target_lang,
        word_category,
        canon,
        name=name,
        description=description if description is not None else f"Existing rule description for {slug}",
    )
    return rule, canon


def _add_renamed_estar_rule(db_session, language_en, target_lang, word_category, *, description=None):
    """The row #45 was filed against: `name` edited away from its catalog entry.

    The catalog entry says the rule teaches present-tense -ar conjugation while
    the rule is named `Usage of estar`, so the two labels contradict each other.
    """
    return _add_rule(
        db_session, language_en, target_lang, word_category,
        name="Usage of estar",
        catalog_name="Present tense regular -ar conjugation",
        slug="present-tense-ar-conjugation",
        description=description,
    )


class TestSimilarityOrZero:
    """The score helper's contract: a number, whatever the inputs are.

    `get_similar_rule_candidates` orders and filters on the value this returns,
    so anything that can reach it as NULL drops the row silently.
    """

    def test_a_null_column_yields_zero_rather_than_null(
        self, db_session, language_en, language_es, word_category
    ):
        canon = _add_canonical_rule(
            db_session, language_en, language_es, word_category,
            name="Present Tense -ar Verbs", slug="present-ar",
        )
        _add_grammar_rule(
            db_session, language_es, word_category, canon,
            name="present tense ar verbs", description=None,
        )

        score = db_session.query(
            _similarity_or_zero(GrammarRule.description, SER_VS_ESTAR_DESCRIPTION)
        ).scalar()

        assert score == 0.0

    def test_a_blank_proposal_field_yields_zero_without_comparing(
        self, db_session, language_en, language_es, word_category
    ):
        canon = _add_canonical_rule(
            db_session, language_en, language_es, word_category,
            name="Ser vs. estar", slug="ser-vs-estar",
        )
        _add_grammar_rule(
            db_session, language_es, word_category, canon,
            name="Ser vs. estar", description=SER_VS_ESTAR_DESCRIPTION,
        )

        score = db_session.query(
            _similarity_or_zero(GrammarRule.description, "   ")
        ).scalar()

        assert score == 0.0


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
            db_session,
            target_language_id=language_es.id,
            name="present tense ar verbs",
            description="Conjugate -ar verbs in the present tense.",
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
            db_session,
            target_language_id=language_es.id,
            name="present tense ar verbs",
            description="Conjugate -ar verbs in the present tense.",
        )

        assert result == []

    def test_a_blank_proposed_title_leaves_the_description_as_the_only_signal(
        self, db_session, language_en, language_es, word_category
    ):
        # The rule's name matches outright, but a blank title contributes no name
        # signal at all, and its filler description scores 0.15942 against the
        # proposed explanation — under the gate. Both values are pinned in
        # test_pg_trgm.py.
        on_name_alone = _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
        )[0]

        result = get_similar_rule_candidates(
            db_session,
            target_language_id=language_es.id,
            name="   ",
            description="Conjugate -ar verbs in the present tense.",
        )

        assert on_name_alone.id not in [candidate.id for candidate in result]

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
            db_session,
            target_language_id=language_es.id,
            name="present tense ar verbs",
            description="Conjugate -ar verbs in the present tense.",
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
            description="Conjugate -ar verbs in the present tense.",
        )

        assert [candidate.id for candidate in result] == [match.id]

    def test_finds_a_duplicate_renamed_to_share_only_a_suffix_word(
        self, db_session, language_en, language_es, word_category
    ):
        match = _add_renamed_estar_rule(
            db_session, language_en, language_es, word_category,
            description=SER_VS_ESTAR_DESCRIPTION,
        )[0]

        result = get_similar_rule_candidates(
            db_session,
            target_language_id=language_es.id,
            name="Ser vs. estar",
            description=SER_VS_ESTAR_DESCRIPTION,
        )

        assert [candidate.id for candidate in result] == [match.id]

    def test_finds_a_duplicate_whose_name_says_nothing_about_the_topic(
        self, db_session, language_en, language_es, word_category
    ):
        # The name scores 0.0652 against "Ser vs. estar", well under the 0.20
        # gate, so only the description can retrieve this. Both values are
        # pinned against pg_trgm 1.6 in test_pg_trgm.py.
        drifted = _add_rule(
            db_session, language_en, language_es, word_category,
            name="Permanent vs. temporary descriptions",
            catalog_name="Ser vs. estar",
            slug="ser-vs-estar",
            description=SER_VS_ESTAR_DESCRIPTION,
        )[0]

        result = get_similar_rule_candidates(
            db_session,
            target_language_id=language_es.id,
            name="Ser vs. estar",
            description=SER_VS_ESTAR_DESCRIPTION,
        )

        assert [candidate.id for candidate in result] == [drifted.id]

    def test_an_unrelated_rule_is_left_out_even_on_its_description(
        self, db_session, language_en, language_es, word_category
    ):
        # Two descriptions of Spanish verbs in the present and past tense share a
        # lot of vocabulary, so this is the case where adding the description to
        # the gate could plausibly drown the real match. It scores 0.1842, under
        # the gate, so it stays out.
        _add_rule(
            db_session, language_en, language_es, word_category,
            name="Reflexive verbs",
            catalog_name="Reflexive verbs",
            slug="reflexive-verbs",
            description=REFLEXIVE_VERBS_DESCRIPTION,
        )

        result = get_similar_rule_candidates(
            db_session,
            target_language_id=language_es.id,
            name="Ser vs. estar",
            description=SER_VS_ESTAR_DESCRIPTION,
        )

        assert result == []

    def test_a_rule_with_no_description_is_still_matched_on_its_name(
        self, db_session, language_en, language_es, word_category
    ):
        # `pg_trgm.similarity()` is NULL when either argument is, and a NULL
        # description is ordinary here, so this is where the score has to stay a
        # number for the rule's name to count for anything.
        canon = _add_canonical_rule(
            db_session, language_en, language_es, word_category,
            name="Present Tense -ar Verbs", slug="present-ar",
        )
        match = _add_grammar_rule(
            db_session, language_es, word_category, canon,
            name="present tense ar verbs", description=None,
        )

        result = get_similar_rule_candidates(
            db_session,
            target_language_id=language_es.id,
            name="present tense ar verbs",
            description="Conjugate -ar verbs in the present tense.",
        )

        assert [candidate.id for candidate in result] == [match.id]

    def test_a_blank_proposed_description_leaves_the_name_as_the_only_signal(
        self, db_session, language_en, language_es, word_category
    ):
        # The name scores 0.0652 against "Ser vs. estar", so this rule is
        # findable only through its description. With no proposed description to
        # match, nothing is left to find it by.
        found_by_description_alone = _add_rule(
            db_session, language_en, language_es, word_category,
            name="Permanent vs. temporary descriptions",
            catalog_name="Ser vs. estar",
            slug="ser-vs-estar",
            description=SER_VS_ESTAR_DESCRIPTION,
        )[0]

        result = get_similar_rule_candidates(
            db_session,
            target_language_id=language_es.id,
            name="Ser vs. estar",
            description="",
        )

        assert found_by_description_alone.id not in [candidate.id for candidate in result]

    def test_a_blank_proposed_title_does_not_discard_a_usable_description(
        self, db_session, language_en, language_es, word_category
    ):
        # Neither field alone is enough to give up on: a proposal with no title
        # is still worth checking against the explanations.
        found_by_description_alone = _add_rule(
            db_session, language_en, language_es, word_category,
            name="Permanent vs. temporary descriptions",
            catalog_name="Ser vs. estar",
            slug="ser-vs-estar",
            description=SER_VS_ESTAR_DESCRIPTION,
        )[0]

        result = get_similar_rule_candidates(
            db_session,
            target_language_id=language_es.id,
            name="",
            description=SER_VS_ESTAR_DESCRIPTION,
        )

        assert [candidate.id for candidate in result] == [found_by_description_alone.id]

    def test_no_candidates_when_the_whole_proposal_is_blank(
        self, db_session, language_en, language_es, word_category
    ):
        _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
        )

        result = get_similar_rule_candidates(
            db_session,
            target_language_id=language_es.id,
            name="   ",
            description="",
        )

        assert result == []

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
            db_session,
            target_language_id=language_es.id,
            name="present tense ar verbs",
            description="Conjugate -ar verbs in the present tense.",
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
            description="Conjugate -ar verbs in the present tense.",
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
            db_session,
            target_language_id=language_es.id,
            name="present tense ar verbs",
            description="Conjugate -ar verbs in the present tense.",
        )

        # pg_trgm scores these against "present tense ar verbs" as 0.7692,
        # 0.6087, 0.5926, 0.4857, 0.4000 and 0.2000, so all six clear the 0.20
        # threshold and the sixth is dropped by MAX_CANDIDATES. These values are
        # pinned in test_pg_trgm.py. The descriptions here score 0.0000 against
        # the proposed one, so the order is decided by name alone.
        assert [candidate.name for candidate in result] == [
            "present tense er verbs",
            "present tense",
            "past tense ar verbs",
            "present tense ar conjugation",
            "preterite tense ar",
        ]

    def test_each_candidate_carries_the_stored_name_and_description(
        self, db_session, language_en, language_es, word_category
    ):
        rule = _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
            description=SER_VS_ESTAR_DESCRIPTION,
        )[0]

        result = get_similar_rule_candidates(
            db_session,
            target_language_id=language_es.id,
            name="present tense ar verbs",
            description=SER_VS_ESTAR_DESCRIPTION,
        )

        assert result[0].name == rule.name
        assert result[0].description == SER_VS_ESTAR_DESCRIPTION


def _parse_candidates(rendered: str) -> list[dict[str, str]]:
    """Read the candidate block back the way the judge receives it, label by label.

    Parsing the rendered prompt rather than the objects behind it is deliberate:
    the judge is only ever handed this text, so a double that read anything else
    would not be exercising what the judge does.
    """
    candidates: list[dict[str, str]] = []
    for line in rendered.splitlines():
        if line.startswith("- id:"):
            candidates.append({"id": line[len("- id:"):].strip()})
        elif candidates and ":" in line:
            label, _, value = line.strip().partition(":")
            candidates[-1][label] = value.strip()
    return candidates


class LabelContradictionJudge:
    """A stand-in for the duplicate judge, faithful in the way #45 records.

    The real judge was called against the local stack with one proposal and one
    candidate, changing only the candidate's catalog link, and returned
    `similar=False` when the rule's own name and its catalog entry name
    disagreed, `similar=True` when they agreed. This double reproduces both: it
    refuses to judge a candidate it cannot resolve, which is what it does when a
    candidate carries two labels that do not describe the same thing, and
    otherwise matches a candidate whose name or description is close enough to
    the proposal.

    Being able to say *no* matters as much as being able to say yes. A double
    that always agreed would pass every test written against it while
    reproducing neither of the verdicts above.

    The abstention branch is the only part of this class that production cannot
    reach, because `_format_candidates` no longer emits a catalog name — that is
    the fix. It stays because without it the double could not reproduce the false
    negative at all, and a double that cannot say no makes "the verdict is
    pinned" an empty claim.
    """

    def __init__(self):
        self.invocations = []

    def invoke(self, prompt_inputs) -> DuplicateJudgeResult:
        self.invocations.append(prompt_inputs)

        matches = []
        for candidate in _parse_candidates(prompt_inputs["candidates"]):
            labels = [candidate["name"]]
            if "catalog name" in candidate:
                labels.append(candidate["catalog name"])
            if any(
                similarity(first_label, second_label) < TRIGRAM_SIMILARITY_THRESHOLD
                for first_label, second_label in itertools.combinations(labels, 2)
            ):
                continue
            score = max(
                similarity(candidate["name"], prompt_inputs["rule_title"]),
                similarity(
                    candidate.get("description", ""),
                    prompt_inputs["rule_explanation"],
                ),
            )
            if score >= TRIGRAM_SIMILARITY_THRESHOLD:
                matches.append((score, candidate["id"]))

        if not matches:
            return DuplicateJudgeResult(similar=False, matched_ids=[])
        ranked = [
            match_id
            for _score, match_id in sorted(matches, key=lambda match: -match[0])
        ]
        return DuplicateJudgeResult(
            similar=True,
            matched_ids=[
                uuid.UUID(match_id) for match_id in ranked[:MAX_RULES_THE_JUDGE_NAMES]
            ],
        )


class TestLabelContradictionJudge:
    """Pins the double to the production verdicts quoted in #45."""

    RULE_ID = "0f4c2a1e-9c53-4a71-8f0d-2b6a1c7d5e83"

    def _prompt(self, *, rule_name, catalog_name, description, proposal_description):
        return {
            "rule_title": "Ser vs. estar",
            "rule_explanation": proposal_description,
            "candidates": (
                f"- id: {self.RULE_ID}\n"
                f"  name: {rule_name}\n"
                f"  catalog name: {catalog_name}\n"
                f"  description: {description}"
            ),
        }

    def test_vetoes_a_candidate_whose_two_labels_contradict_each_other(self):
        # `Usage of estar` against `Present tense regular -ar conjugation` scores
        # 0.02, far below the 0.20 bar, so the two labels cannot both be right.
        # The description matches the proposal exactly, so the contradicting
        # labels are the only thing that can produce a refusal here.
        verdict = LabelContradictionJudge().invoke(
            self._prompt(
                rule_name="Usage of estar",
                catalog_name="Present tense regular -ar conjugation",
                description=SER_VS_ESTAR_DESCRIPTION,
                proposal_description=SER_VS_ESTAR_DESCRIPTION,
            )
        )

        assert verdict.similar is False

    def test_matches_a_candidate_whose_two_labels_agree(self):
        verdict = LabelContradictionJudge().invoke(
            self._prompt(
                rule_name="Ser vs. estar",
                catalog_name="Ser vs. estar",
                description=SER_VS_ESTAR_DESCRIPTION,
                proposal_description=SER_VS_ESTAR_DESCRIPTION,
            )
        )

        assert verdict.similar is True
        assert verdict.matched_ids == [uuid.UUID(self.RULE_ID)]

    def test_reports_no_match_for_an_unrelated_candidate(self):
        verdict = LabelContradictionJudge().invoke(
            {
                "rule_title": "Ser vs. estar",
                "rule_explanation": SER_VS_ESTAR_DESCRIPTION,
                "candidates": (
                    f"- id: {self.RULE_ID}\n"
                    "  name: Basic negation\n"
                    f"  description: {REFLEXIVE_VERBS_DESCRIPTION}"
                ),
            }
        )

        assert verdict.similar is False


class TestCheckSimilarRules:
    def test_names_every_matching_rule_best_first(
        self, db_session, language_en, language_es, word_category
    ):
        """All three ser/estar rules, ordered by how well each fits.

        The two rules the admin already has both teach part of what the proposal
        teaches, and retrieval already surfaces both — only the singular judge
        contract stood between that and a card naming them. Scores against the
        proposal: 1.0 on the name, 0.3563 on the description, 0.3333 on a reworded
        name.
        """
        judge = LabelContradictionJudge()
        exact = _add_rule(
            db_session, language_en, language_es, word_category,
            name="Ser vs. estar", catalog_name="Ser vs. estar", slug="ser-vs-estar",
        )[0]
        by_description = _add_rule(
            db_session, language_en, language_es, word_category,
            name="Usage of verb estar", catalog_name="Ser vs. estar",
            slug="ser-vs-estar-estar", description=SER_VS_ESTAR_DESCRIPTION,
        )[0]
        reworded = _add_rule(
            db_session, language_en, language_es, word_category,
            name="Ser and estar: which to use", catalog_name="Ser vs. estar",
            slug="ser-vs-estar-which",
        )[0]

        with patch("crud.rule_similarity.judge_chain", judge):
            result = check_similar_rules(
                db_session,
                target_language_id=language_es.id,
                proposed_title="Ser vs. estar",
                proposed_description=SER_VS_ESTAR_DESCRIPTION,
            )

        assert result.similar is True
        assert [rule.id for rule in result.existing_rules] == [
            exact.id, by_description.id, reworded.id,
        ]

    def test_the_filed_estar_rule_is_named_but_the_ser_rule_misses_the_gate_here(
        self, db_session, language_en, language_es, word_category
    ):
        """The rows #48 was filed against, and a gap in the evidence filed with it.

        #48 quotes real pg_trgm 1.6 scoring `Usage of verb ser` at 0.2342 against
        the proposal — over the 0.20 gate, and recorded as retrieved. The SQLite
        stand-in computes 0.1923 for the same pair, so under pytest that rule is
        filtered before the judge ever sees it and only `Usage of verb estar` comes
        back. Nothing in this change decides that; retrieval's gate is unchanged and
        its scores are pinned in test_pg_trgm.py, but the two disagree for this pair.

        Both facts are asserted rather than papered over with a fixture tuned to
        agree, because if the stand-in is the wrong one, the tests above it are
        resting on a similarity function that does not match production.
        """
        estar = _add_rule(
            db_session, language_en, language_es, word_category,
            name="Usage of verb estar", catalog_name="Ser vs. estar",
            slug="ser-vs-estar-estar", description=SER_VS_ESTAR_DESCRIPTION,
        )[0]
        ser = _add_rule(
            db_session, language_en, language_es, word_category,
            name="Usage of verb ser", catalog_name="Ser vs. estar",
            slug="ser-vs-estar-ser", description=None,
        )[0]

        with patch("crud.rule_similarity.judge_chain", LabelContradictionJudge()):
            result = check_similar_rules(
                db_session,
                target_language_id=language_es.id,
                proposed_title="Ser vs. estar",
                proposed_description=SER_VS_ESTAR_DESCRIPTION,
            )

        assert result.similar is True
        assert [rule.id for rule in result.existing_rules] == [estar.id]
        assert ser.id not in [rule.id for rule in result.existing_rules]
        assert similarity("Usage of verb ser", "Ser vs. estar") < (
            TRIGRAM_SIMILARITY_THRESHOLD
        )

    @patch("crud.rule_similarity.judge_chain")
    def test_both_stored_ser_estar_rules_reach_the_card_together(
        self, mock_judge, db_session, language_en, language_es, word_category
    ):
        """The card #48 asked for: both of the admin's ser/estar rules, named.

        `ser` carries the shared description here so the SQLite stand-in retrieves
        it; the filed row's description is NULL and its name scores 0.1923, so
        without that the rule never reaches the judge under pytest at all. What is
        under test is the card, so the fixture has to make the collision real.

        Which of the two leads is the real judge's call, weighing meaning rather
        than trigrams. That ranking is pinned by
        `test_names_every_matching_rule_best_first` above, where the double scores
        the candidates itself; asserting estar first here would only be asserting
        the order this mock was written in.
        """
        estar = _add_rule(
            db_session, language_en, language_es, word_category,
            name="Usage of verb estar", catalog_name="Ser vs. estar",
            slug="ser-vs-estar-estar", description=SER_VS_ESTAR_DESCRIPTION,
        )[0]
        ser = _add_rule(
            db_session, language_en, language_es, word_category,
            name="Usage of verb ser", catalog_name="Ser vs. estar",
            slug="ser-vs-estar-ser", description=SER_VS_ESTAR_DESCRIPTION,
        )[0]
        mock_judge.invoke.return_value = DuplicateJudgeResult(
            similar=True, matched_ids=[estar.id, ser.id]
        )

        result = check_similar_rules(
            db_session,
            target_language_id=language_es.id,
            proposed_title="Ser vs. estar",
            proposed_description=SER_VS_ESTAR_DESCRIPTION,
        )

        assert result.similar is True
        assert [rule.name for rule in result.existing_rules] == [
            "Usage of verb estar", "Usage of verb ser",
        ]

    def test_a_rule_renamed_away_from_its_catalog_entry_is_still_flagged(
        self, db_session, language_en, language_es, word_category
    ):
        judge = LabelContradictionJudge()
        rule = _add_renamed_estar_rule(
            db_session, language_en, language_es, word_category,
            description=SER_VS_ESTAR_DESCRIPTION,
        )[0]

        with patch("crud.rule_similarity.judge_chain", judge):
            result = check_similar_rules(
                db_session,
                target_language_id=language_es.id,
                proposed_title="Ser vs. estar",
                proposed_description=SER_VS_ESTAR_DESCRIPTION,
            )

        assert result.similar is True
        assert [found.id for found in result.existing_rules] == [rule.id]
        assert result.existing_rules[0].name == "Usage of estar"

    def test_a_duplicate_whose_name_says_nothing_about_the_topic_is_still_flagged(
        self, db_session, language_en, language_es, word_category
    ):
        judge = LabelContradictionJudge()
        rule = _add_rule(
            db_session, language_en, language_es, word_category,
            name="Permanent vs. temporary descriptions",
            catalog_name="Ser vs. estar",
            slug="ser-vs-estar",
            description=SER_VS_ESTAR_DESCRIPTION,
        )[0]

        with patch("crud.rule_similarity.judge_chain", judge):
            result = check_similar_rules(
                db_session,
                target_language_id=language_es.id,
                proposed_title="Ser vs. estar",
                proposed_description=SER_VS_ESTAR_DESCRIPTION,
            )

        assert result.similar is True
        assert [found.id for found in result.existing_rules] == [rule.id]

    def test_the_judge_is_never_handed_the_catalog_entrys_name(
        self, db_session, language_en, language_es, word_category
    ):
        judge = LabelContradictionJudge()
        rule, canon = _add_renamed_estar_rule(
            db_session, language_en, language_es, word_category,
            description=SER_VS_ESTAR_DESCRIPTION,
        )

        with patch("crud.rule_similarity.judge_chain", judge):
            check_similar_rules(
                db_session,
                target_language_id=language_es.id,
                proposed_title="Ser vs. estar",
                proposed_description=SER_VS_ESTAR_DESCRIPTION,
            )

        rendered = judge.invocations[0]["candidates"]
        assert rule.name in rendered
        assert SER_VS_ESTAR_DESCRIPTION in rendered
        assert canon.name not in rendered

    def test_the_judge_receives_the_proposal_and_each_stored_name_and_description(
        self, db_session, language_en, language_es, word_category
    ):
        judge = LabelContradictionJudge()
        rule = _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
            description=SER_VS_ESTAR_DESCRIPTION,
        )[0]

        with patch("crud.rule_similarity.judge_chain", judge):
            check_similar_rules(
                db_session,
                target_language_id=language_es.id,
                proposed_title="present tense ar verbs",
                proposed_description="Conjugate -ar verbs in the present tense.",
            )

        prompt_inputs = judge.invocations[0]
        assert prompt_inputs["rule_title"] == "present tense ar verbs"
        assert prompt_inputs["rule_explanation"] == (
            "Conjugate -ar verbs in the present tense."
        )
        assert str(rule.id) in prompt_inputs["candidates"]
        assert rule.name in prompt_inputs["candidates"]
        assert SER_VS_ESTAR_DESCRIPTION in prompt_inputs["candidates"]

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
        assert result.existing_rules == []
        mock_judge.invoke.assert_not_called()

    @patch("crud.rule_similarity.judge_chain")
    def test_judge_match_returns_the_existing_rule_in_a_list(
        self, mock_judge, db_session, language_en, language_es, word_category
    ):
        rule = _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
        )[0]
        mock_judge.invoke.return_value = DuplicateJudgeResult(
            similar=True, matched_ids=[rule.id]
        )

        result = check_similar_rules(
            db_session,
            target_language_id=language_es.id,
            proposed_title="present tense ar verbs",
            proposed_description="Conjugate -ar verbs in the present tense.",
        )

        assert result.similar is True
        assert [found.id for found in result.existing_rules] == [rule.id]
        assert result.existing_rules[0].name == rule.name
        assert result.existing_rules[0].description == rule.description

    @patch("crud.rule_similarity.judge_chain")
    def test_a_second_rule_sharing_the_same_catalog_entry_is_still_offered(
        self, mock_judge, db_session, language_en, language_es, word_category
    ):
        _, canon = _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
        )
        second = _add_grammar_rule(
            db_session, language_es, word_category, canon,
            name="present tense ar verbs in detail",
            description="The same rule, at greater length.",
        )
        mock_judge.invoke.return_value = DuplicateJudgeResult(
            similar=True, matched_ids=[second.id]
        )

        result = check_similar_rules(
            db_session,
            target_language_id=language_es.id,
            proposed_title="present tense ar verbs",
            proposed_description="Conjugate -ar verbs in the present tense.",
        )

        assert result.similar is True
        assert [found.id for found in result.existing_rules] == [second.id]
        assert result.existing_rules[0].name == "present tense ar verbs in detail"

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
            similar=False, matched_ids=[]
        )

        result = check_similar_rules(
            db_session,
            target_language_id=language_es.id,
            proposed_title="present tense ar verbs",
            proposed_description="Conjugate -ar verbs in the present tense.",
        )

        assert result.similar is False
        assert result.existing_rules == []

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
            similar=True, matched_ids=[uuid.uuid4()]
        )

        result = check_similar_rules(
            db_session,
            target_language_id=language_es.id,
            proposed_title="present tense ar verbs",
            proposed_description="Conjugate -ar verbs in the present tense.",
        )

        assert result.similar is False
        assert result.existing_rules == []

    @patch("crud.rule_similarity.judge_chain")
    def test_more_than_three_matches_are_capped_here_not_only_in_the_prompt(
        self, mock_judge, db_session, language_en, language_es, word_category
    ):
        """The card names at most three, whatever the judge asks for.

        Retrieval offers up to five candidates and the prompt asks for three, so a
        judge returning five is disobeying an instruction. The cap still applies:
        what an admin sees should not rest on the judge keeping to the request.
        """
        names = [
            "present subjunctive mood",
            "present tense ar conjugation",
            "preterite tense ar",
            "past tense ar verbs",
            "present tense",
        ]
        rules = [
            _add_rule(
                db_session, language_en, language_es, word_category,
                name=name, catalog_name=f"Catalog {name}", slug=f"rule-{index}",
            )[0]
            for index, name in enumerate(names)
        ]
        mock_judge.invoke.return_value = DuplicateJudgeResult(
            similar=True, matched_ids=[rule.id for rule in rules]
        )

        result = check_similar_rules(
            db_session,
            target_language_id=language_es.id,
            proposed_title="present tense ar verbs",
            proposed_description="Conjugate -ar verbs in the present tense.",
        )

        assert result.similar is True
        assert [rule.name for rule in result.existing_rules] == names[:3]

    @patch("crud.rule_similarity.judge_chain")
    def test_one_match_among_several_candidates_is_not_padded(
        self, mock_judge, db_session, language_en, language_es, word_category
    ):
        """The judge endorsed one rule, so the card names one.

        Retrieval offers everything that clears the threshold and says nothing about
        which of them are duplicates. Padding the card out to three with the rest
        would claim the admin already has rules the judge judged to be different.
        """
        rules = [
            _add_rule(
                db_session, language_en, language_es, word_category,
                name=name, catalog_name=f"Catalog {name}", slug=f"rule-{index}",
            )[0]
            for index, name in enumerate([
                "present tense ar verbs",
                "present tense er verbs",
                "past tense ar verbs",
            ])
        ]
        mock_judge.invoke.return_value = DuplicateJudgeResult(
            similar=True, matched_ids=[rules[0].id]
        )

        result = check_similar_rules(
            db_session,
            target_language_id=language_es.id,
            proposed_title="present tense ar verbs",
            proposed_description="Conjugate -ar verbs in the present tense.",
        )

        assert result.similar is True
        assert [rule.name for rule in result.existing_rules] == [
            "present tense ar verbs",
        ]

    @patch("crud.rule_similarity.judge_chain")
    def test_a_repeated_id_is_named_once(
        self, mock_judge, db_session, language_en, language_es, word_category
    ):
        """A judge that names the same rule twice still gets one entry on the card.

        The card counts its entries, so a repeat would read as "3 rules" when the
        admin has two.
        """
        rule = _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
        )[0]
        mock_judge.invoke.return_value = DuplicateJudgeResult(
            similar=True, matched_ids=[rule.id, rule.id]
        )

        result = check_similar_rules(
            db_session,
            target_language_id=language_es.id,
            proposed_title="present tense ar verbs",
            proposed_description="Conjugate -ar verbs in the present tense.",
        )

        assert result.similar is True
        assert [rule.name for rule in result.existing_rules] == [
            "present tense ar verbs",
        ]

    @patch("crud.rule_similarity.judge_chain")
    def test_a_known_id_alongside_an_invented_one_still_names_the_known_rule(
        self, mock_judge, db_session, language_en, language_es, word_category
    ):
        """An id that was never offered is dropped, not treated as losing the match.

        The judge is naming from free text, so one hallucinated id alongside a real
        one should cost only the invented one. Only when nothing survives does the
        result fall back to not similar, which is the case the neighbouring test
        pins.
        """
        rule = _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
        )[0]
        mock_judge.invoke.return_value = DuplicateJudgeResult(
            similar=True, matched_ids=[uuid.uuid4(), rule.id]
        )

        result = check_similar_rules(
            db_session,
            target_language_id=language_es.id,
            proposed_title="present tense ar verbs",
            proposed_description="Conjugate -ar verbs in the present tense.",
        )

        assert result.similar is True
        assert [rule.id for rule in result.existing_rules] == [rule.id]

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
            similar=True, matched_ids=[rule.id]
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

    def test_the_candidate_names_and_the_verdict_are_logged(
        self, db_session, language_en, language_es, word_category, caplog
    ):
        rule = _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
        )[0]

        with patch("crud.rule_similarity.judge_chain", LabelContradictionJudge()):
            with caplog.at_level(logging.INFO, logger="crud.rule_similarity"):
                check_similar_rules(
                    db_session,
                    target_language_id=language_es.id,
                    proposed_title="present tense ar verbs",
                    proposed_description="Conjugate -ar verbs in the present tense.",
                )

        assert any(
            rule.name in record.getMessage() and "similar=True" in record.getMessage()
            for record in caplog.records
        ), [record.getMessage() for record in caplog.records]

    def test_an_llm_failure_is_logged_and_reported_as_not_similar(
        self, db_session, language_en, language_es, word_category, caplog
    ):
        _add_rule(
            db_session, language_en, language_es, word_category,
            name="present tense ar verbs",
            catalog_name="Present Tense -ar Verbs",
            slug="present-ar",
        )

        with patch("crud.rule_similarity.judge_chain") as mock_judge:
            mock_judge.invoke.side_effect = RuntimeError("upstream is down")
            with caplog.at_level(logging.INFO, logger="crud.rule_similarity"):
                result = check_similar_rules(
                    db_session,
                    target_language_id=language_es.id,
                    proposed_title="present tense ar verbs",
                    proposed_description="Conjugate -ar verbs in the present tense.",
                )

        assert result.similar is False
        assert result.existing_rules == []
        logged_failures = [
            record
            for record in caplog.records
            if record.exc_info is not None
            and isinstance(record.exc_info[1], RuntimeError)
            and str(record.exc_info[1]) == "upstream is down"
        ]
        assert logged_failures, [
            (record.getMessage(), record.exc_info) for record in caplog.records
        ]
