from crud.rules import create_grammar_rule
from models.grammar_rules import GrammarRule


class TestCreateGrammarRule:
    def test_stores_canonical_link_and_copied_word_category(
        self, db_session, language_es, canonical_rule
    ):
        rule = create_grammar_rule(
            db=db_session,
            title="Noun Gender",
            description="Masculine vs feminine",
            language_id=language_es.id,
            word_category_id=canonical_rule.word_category_id,
            canonical_rule_id=canonical_rule.id,
        )

        persisted = db_session.query(GrammarRule).filter(GrammarRule.id == rule.id).one()
        assert persisted.canonical_rule_id == canonical_rule.id
        assert persisted.word_category_id == canonical_rule.word_category_id
        assert persisted.name == "Noun Gender"
        assert persisted.description == "Masculine vs feminine"
