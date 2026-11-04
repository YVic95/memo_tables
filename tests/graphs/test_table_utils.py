from graphs.table_utils import COLUMN_ROLES, DEFAULT_COLUMN_ROLES, column_roles

NOUN_ROLES = {0: "form", 1: "explanation", 2: "example"}
VERB_ROLES = {0: "label", 1: "form", 2: "example", 3: "explanation"}


class TestColumnRoles:
    def test_noun_roles_are_explicitly_mapped(self):
        assert COLUMN_ROLES["noun"] == NOUN_ROLES

    def test_noun_returns_form_explanation_example(self):
        assert column_roles("noun") == NOUN_ROLES

    def test_verb_roles_are_unchanged(self):
        assert column_roles("verb") == VERB_ROLES

    def test_unsupported_categories_fall_back_to_default(self):
        for slug in ("adjective", "adverb", "pronoun", "unknown"):
            assert column_roles(slug) == DEFAULT_COLUMN_ROLES
