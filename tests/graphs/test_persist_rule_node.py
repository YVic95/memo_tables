from crud.canonical_rules import get_missing_canonical_rules_for_pair
from graphs.nodes.persist_rule import persist_rule_node
from models.grammar_rules import GrammarRule


class TestPersistRuleNode:
    def test_persists_rule_linked_to_its_catalog_entry(
        self, db_session, language_es, canonical_rule
    ):
        result = persist_rule_node(
            {
                "db": db_session,
                "rule_title": "Noun Gender",
                "rule_explanation": "Masculine vs feminine",
                "target_language_id": language_es.id,
                "word_category_id": canonical_rule.word_category_id,
                "canonical_rule_id": canonical_rule.id,
            }
        )

        persisted = (
            db_session.query(GrammarRule)
            .filter(GrammarRule.id == result["grammar_rule_id"])
            .one()
        )
        assert persisted.canonical_rule_id == canonical_rule.id
        assert persisted.word_category_id == canonical_rule.word_category_id

    def test_preserves_existing_state_fields(self, db_session, language_es, canonical_rule):
        result = persist_rule_node(
            {
                "db": db_session,
                "rule_title": "Noun Gender",
                "rule_explanation": "Masculine vs feminine",
                "target_language_id": language_es.id,
                "native_language": "English",
                "word_category_id": canonical_rule.word_category_id,
                "canonical_rule_id": canonical_rule.id,
            }
        )

        assert result["native_language"] == "English"
        assert result["canonical_rule_id"] == canonical_rule.id

    def test_created_rule_is_excluded_from_missing_suggestions(
        self, db_session, language_en, language_es, canonical_rule
    ):
        persist_rule_node(
            {
                "db": db_session,
                "rule_title": "Noun Gender",
                "rule_explanation": "Masculine vs feminine",
                "target_language_id": language_es.id,
                "word_category_id": canonical_rule.word_category_id,
                "canonical_rule_id": canonical_rule.id,
            }
        )

        missing = get_missing_canonical_rules_for_pair(
            db_session, language_en.id, language_es.id
        )

        assert missing == []
