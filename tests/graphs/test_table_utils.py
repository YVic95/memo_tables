from graphs.table_utils import COLUMN_ROLES, DEFAULT_COLUMN_ROLES, column_roles

VERB_ROLES = {0: "label", 1: "form", 2: "example", 3: "explanation"}


class TestColumnRoles:
    def test_noun_no_longer_has_a_three_column_mapping(self):
        assert "noun" not in COLUMN_ROLES

    def test_verb_roles_are_unchanged(self):
        assert column_roles("verb") == VERB_ROLES

    def test_unsupported_categories_fall_back_to_default(self):
        for slug in ("noun", "adjective", "adverb", "pronoun", "unknown"):
            assert column_roles(slug) == DEFAULT_COLUMN_ROLES
