import uuid
from unittest.mock import patch

import pytest

from graphs.models import CatalogRule, ProposedCatalogRules
from graphs.nodes.propose_rules_node import propose_rules_node
from models.canonical_rules import CanonicalRule
from models.grammar_rules import GrammarRule
from models.word_categories import WordCategory


@pytest.fixture()
def verb_category(db_session):
    category = WordCategory(name="Verbs", slug="verb")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


def _add_catalog_rule(db_session, language_en, language_es, word_category, *, slug, level, position):
    rule = CanonicalRule(
        native_language_id=language_en.id,
        target_language_id=language_es.id,
        word_category_id=word_category.id,
        level=level,
        name=slug.replace("-", " ").title(),
        description=f"Description for {slug}",
        position=position,
        slug=slug,
        is_active=True,
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule


def _link_rule(db_session, language_es, word_category, canonical_rule):
    rule = GrammarRule(
        name=canonical_rule.name,
        description=canonical_rule.description,
        language_id=language_es.id,
        word_category_id=word_category.id,
        canonical_rule_id=canonical_rule.id,
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule


def _state(db_session, language_en, language_es, **overrides):
    state = {
        "db": db_session,
        "native_language": language_en.name,
        "target_language": language_es.name,
        "native_language_id": language_en.id,
        "target_language_id": language_es.id,
        "proposed_rules": [],
        "message": "",
    }
    state.update(overrides)
    return state


def _rules(*entries):
    return ProposedCatalogRules(
        rules=[CatalogRule(**entry) for entry in entries]
    )


class TestProposeRulesNode:
    @patch("graphs.nodes.propose_rules_node.propose_rules_chain")
    def test_injects_eligible_candidates_into_prompt(
        self, mock_chain, db_session, language_en, language_es, verb_category
    ):
        candidate = _add_catalog_rule(
            db_session, language_en, language_es, verb_category,
            slug="present-tense-ar-conjugation", level="A1", position=1,
        )
        mock_chain.invoke.return_value = _rules(
            {
                "title": candidate.name,
                "explanation": candidate.description,
                "canonical_rule_id": candidate.id,
            },
        )
        state = _state(db_session, language_en, language_es)

        propose_rules_node(state)

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert call_kwargs["native_language"] == "English"
        assert call_kwargs["target_language"] == "Spanish"
        assert candidate.name in call_kwargs["candidates"]
        assert str(candidate.id) in call_kwargs["candidates"]
        assert candidate.description in call_kwargs["candidates"]

    @patch("graphs.nodes.propose_rules_node.propose_rules_chain")
    def test_each_returned_rule_carries_canonical_rule_id(
        self, mock_chain, db_session, language_en, language_es, verb_category
    ):
        candidate = _add_catalog_rule(
            db_session, language_en, language_es, verb_category,
            slug="present-tense-ar-conjugation", level="A1", position=1,
        )
        mock_chain.invoke.return_value = _rules(
            {
                "title": candidate.name,
                "explanation": candidate.description,
                "canonical_rule_id": candidate.id,
            },
        )
        state = _state(db_session, language_en, language_es)

        result = propose_rules_node(state)

        assert result["proposed_rules"] == [
            {
                "title": candidate.name,
                "explanation": candidate.description,
                "canonical_rule_id": str(candidate.id),
            }
        ]

    @patch("graphs.nodes.propose_rules_node.propose_rules_chain")
    def test_drops_rules_outside_the_eligible_set(
        self, mock_chain, db_session, language_en, language_es, verb_category
    ):
        candidate = _add_catalog_rule(
            db_session, language_en, language_es, verb_category,
            slug="present-tense-ar-conjugation", level="A1", position=1,
        )
        mock_chain.invoke.return_value = _rules(
            {
                "title": candidate.name,
                "explanation": candidate.description,
                "canonical_rule_id": candidate.id,
            },
            {
                "title": "Invented rule",
                "explanation": "Not in the catalog",
                "canonical_rule_id": uuid.uuid4(),
            },
        )
        state = _state(db_session, language_en, language_es)

        result = propose_rules_node(state)

        assert len(result["proposed_rules"]) == 1
        assert result["proposed_rules"][0]["canonical_rule_id"] == str(candidate.id)

    @patch("graphs.nodes.propose_rules_node.propose_rules_chain")
    def test_orders_returned_rules_by_catalog_order(
        self, mock_chain, db_session, language_en, language_es, verb_category
    ):
        a1_rule = _add_catalog_rule(
            db_session, language_en, language_es, verb_category,
            slug="a1-rule", level="A1", position=1,
        )
        a2_rule = _add_catalog_rule(
            db_session, language_en, language_es, verb_category,
            slug="a2-rule", level="A2", position=1,
        )
        mock_chain.invoke.return_value = _rules(
            {
                "title": a2_rule.name,
                "explanation": a2_rule.description,
                "canonical_rule_id": a2_rule.id,
            },
            {
                "title": a1_rule.name,
                "explanation": a1_rule.description,
                "canonical_rule_id": a1_rule.id,
            },
        )
        state = _state(db_session, language_en, language_es)

        result = propose_rules_node(state)

        assert [rule["canonical_rule_id"] for rule in result["proposed_rules"]] == [
            str(a1_rule.id),
            str(a2_rule.id),
        ]

    @patch("graphs.nodes.propose_rules_node.propose_rules_chain")
    def test_caps_returned_rules_at_five(
        self, mock_chain, db_session, language_en, language_es, verb_category
    ):
        rules = []
        entries = []
        for i in range(7):
            rule = _add_catalog_rule(
                db_session, language_en, language_es, verb_category,
                slug=f"rule-{i}", level="A1", position=i + 1,
            )
            rules.append(
                {
                    "title": rule.name,
                    "explanation": rule.description,
                    "canonical_rule_id": rule.id,
                }
            )
            entries.append(rule)
        mock_chain.invoke.return_value = _rules(*rules)
        state = _state(db_session, language_en, language_es)

        result = propose_rules_node(state)

        assert len(result["proposed_rules"]) == 5
        expected_ids = [str(entries[i].id) for i in range(5)]
        assert [rule["canonical_rule_id"] for rule in result["proposed_rules"]] == expected_ids

    @patch("graphs.nodes.propose_rules_node.propose_rules_chain")
    def test_exhausted_pair_returns_empty_list_and_message_without_llm(
        self, mock_chain, db_session, language_en, language_es, verb_category
    ):
        catalog_rule = _add_catalog_rule(
            db_session, language_en, language_es, verb_category,
            slug="already-done", level="A1", position=1,
        )
        _link_rule(db_session, language_es, verb_category, catalog_rule)
        state = _state(db_session, language_en, language_es)

        result = propose_rules_node(state)

        assert result["proposed_rules"] == []
        assert result["message"]
        mock_chain.invoke.assert_not_called()

    @patch("graphs.nodes.propose_rules_node.propose_rules_chain")
    def test_deduplicates_repeated_canonical_ids(
        self, mock_chain, db_session, language_en, language_es, verb_category
    ):
        entries = [
            _add_catalog_rule(
                db_session, language_en, language_es, verb_category,
                slug=f"rule-{i}", level="A1", position=i + 1,
            )
            for i in range(5)
        ]
        returned = _rules(
            {"title": entries[0].name, "explanation": entries[0].description, "canonical_rule_id": entries[0].id},
            {"title": entries[0].name, "explanation": entries[0].description, "canonical_rule_id": entries[0].id},
            {"title": entries[1].name, "explanation": entries[1].description, "canonical_rule_id": entries[1].id},
            {"title": entries[2].name, "explanation": entries[2].description, "canonical_rule_id": entries[2].id},
            {"title": entries[3].name, "explanation": entries[3].description, "canonical_rule_id": entries[3].id},
            {"title": entries[4].name, "explanation": entries[4].description, "canonical_rule_id": entries[4].id},
        )
        mock_chain.invoke.return_value = returned
        state = _state(db_session, language_en, language_es)

        result = propose_rules_node(state)

        ids = [rule["canonical_rule_id"] for rule in result["proposed_rules"]]
        assert len(ids) == 5
        assert len(set(ids)) == 5

    @patch("graphs.nodes.propose_rules_node.propose_rules_chain")
    def test_preserves_other_state_fields(
        self, mock_chain, db_session, language_en, language_es, verb_category
    ):
        candidate = _add_catalog_rule(
            db_session, language_en, language_es, verb_category,
            slug="some-rule", level="A1", position=1,
        )
        mock_chain.invoke.return_value = _rules(
            {
                "title": candidate.name,
                "explanation": candidate.description,
                "canonical_rule_id": candidate.id,
            },
        )
        state = _state(db_session, language_en, language_es, native_language="Custom")

        result = propose_rules_node(state)

        assert result["native_language"] == "Custom"
        assert result["target_language"] == "Spanish"