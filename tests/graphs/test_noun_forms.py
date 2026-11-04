from graphs.noun_forms import citation_form, noun_keys, singular_form


class TestNounKeys:
    def test_definite_plural_matches_the_singular(self):
        assert noun_keys("las mesas", "Spanish") & noun_keys("la mesa", "Spanish")

    def test_indefinite_article_matches_the_definite_form(self):
        assert noun_keys("una mesa", "Spanish") & noun_keys("la mesa", "Spanish")

    def test_different_nouns_do_not_collide(self):
        assert not noun_keys("la mesa", "Spanish") & noun_keys("el gato", "Spanish")

    def test_english_articles_and_plurals_are_normalized(self):
        assert noun_keys("the tables", "English") & noun_keys("a table", "English")


class TestCitationForm:
    def test_converts_a_plural_definite_form_to_the_singular(self):
        assert citation_form("las mesas", "Spanish") == "la mesa"

    def test_converts_an_indefinite_form_to_the_definite(self):
        assert citation_form("una mesa", "Spanish") == "la mesa"
        assert citation_form("un gato", "Spanish") == "el gato"

    def test_keeps_a_singular_definite_form(self):
        assert citation_form("la mesa", "Spanish") == "la mesa"

    def test_handles_english_plurals(self):
        assert citation_form("the tables", "English") == "the table"

    def test_returns_none_when_there_is_no_article(self):
        assert citation_form("mesas", "Spanish") is None


class TestSingularForm:
    def test_singularizes_without_adding_an_article(self):
        assert singular_form("mesas", "Spanish") == "mesa"
