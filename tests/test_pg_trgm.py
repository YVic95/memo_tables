"""The `similarity()` stand-in must reproduce `pg_trgm`, not approximate it.

Every expected value here was measured against `pg_trgm` 1.6 running in the
local Supabase Postgres. The stand-in exists so SQL predicates calling
`similarity()` can run against the in-memory SQLite session in `conftest.py`;
if it disagrees with `pg_trgm` then the tests it feeds can disagree with
production while staying green. The one place `tests/pg_trgm.py` knowingly
still diverges is documented on `_is_word_character` there.
"""

import os

import pytest
from sqlalchemy import text

from tests.pg_trgm import similarity, trigrams

# similarity() returns `real` in Postgres, so allow for float32 rounding.
FLOAT32_TOLERANCE = 1e-6

# (left, right, similarity as pg_trgm 1.6 reported it)
PG_TRGM_SIMILARITIES = [
    # The pair from the duplicate-detection false negative: the stored rule
    # "Usage of estar" scored below the retrieval threshold in production, so
    # it was never offered to the judge, so no duplicate warning appeared.
    ("Usage of estar", "Ser vs. estar", 0.272727),
    ("present subjunctive mood", "present tense ar verbs", 0.2),
    ("preterite imperfect tense", "present tense ar verbs", 0.225),
    # Case, punctuation, whitespace and word order are all insignificant.
    ("Ser vs. estar", "SER VS. ESTAR", 1.0),
    ("Ser vs. estar", "Ser vs estar", 1.0),
    ("Ser vs. estar", "Ser   vs.    estar", 1.0),
    ("Ser vs. estar", "Ser-vs_estar", 1.0),
    ("Ser vs. estar", "estar vs. Ser", 1.0),
    ("Ser vs. estar", "  ser VS estar!  ", 1.0),
    ("present tense ar verbs", "present tense ar verbs", 1.0),
    # Sharing nothing scores near zero rather than exactly zero.
    ("the cat sat on the mat", "present tense ar verbs", 0.025641),
    ("Noun Gender", "the cat sat on the mat", 0.0),
    # Words shorter than a trigram are kept, not dropped.
    ("of", "of", 1.0),
    ("a", "a", 1.0),
    ("ab", "ab", 1.0),
    ("aaaa", "aaaa", 1.0),
    ("aaaa", "aa", 0.75),
    ("aa", "a", 0.25),
    ("aaaa", "a", 0.2),
    ("of estar", "estar", 0.666667),
    # Digits are word characters; '.' and 'x' are not.
    ("Level A1 verbs", "level a1 verb", 0.8125),
    ("0x1F 2.5", "0x1f 25", 0.545455),
    # Inputs with no word characters at all.
    ("", "", 0.0),
    ("", "present tense ar verbs", 0.0),
    ("   ", "---", 0.0),
    # Accented letters are word characters, compared as characters.
    ("año nuevo", "ano nuevo", 0.538462),
    ("café au lait", "cafe au lait", 0.733333),
    ("niño pequeño", "nino pequeno", 0.411765),
    # Spreads either side of the 0.20 retrieval threshold, and lands on it.
    ("present tense er verbs", "present tense ar verbs", 0.769231),
    ("present tense", "present tense ar verbs", 0.608696),
    ("present tense ar conjugation", "present tense ar verbs", 0.485714),
    ("preterite tense ar", "present tense ar verbs", 0.4),
    ("past tense ar verbs", "present tense ar verbs", 0.592593),
    ("preterite imperfect tense", "present tense ar conjugation", 0.195652),
]

# (text, len(show_trgm(text)) as pg_trgm 1.6 reported it)
PG_TRGM_TRIGRAM_COUNTS = [
    ("", 0),
    ("  ", 0),
    ("---", 0),
    ("a", 2),
    ("of", 3),
    ("ab", 3),
    ("aaaa", 4),
    ("0x1F 2.5", 9),
    ("Level A1 verbs", 15),
    ("año", 4),
    ("café", 5),
]


def similarity_case_ids():
    return [f"{left!r}~{right!r}" for left, right, _expected in PG_TRGM_SIMILARITIES]


def trigram_case_ids():
    return [repr(text) for text, _expected_count in PG_TRGM_TRIGRAM_COUNTS]


class TestTrigrams:
    def test_lowercases_before_extracting(self):
        assert trigrams("ABC") == trigrams("abc")

    def test_pads_each_word_with_two_leading_and_one_trailing_space(self):
        assert trigrams("word") == {"  w", " wo", "wor", "ord", "rd "}

    def test_keeps_words_shorter_than_a_trigram(self):
        assert trigrams("a") == {"  a", " a "}
        assert trigrams("of") == {"  o", " of", "of "}

    def test_splits_words_on_punctuation_and_whitespace(self):
        assert trigrams("a-b") == trigrams("a") | trigrams("b")
        assert trigrams("a b") == trigrams("a") | trigrams("b")

    def test_never_spans_two_words(self):
        assert "a b" not in trigrams("a b")
        assert trigrams("a b") == {"  a", " a ", "  b", " b "}

    def test_collapses_repeated_trigrams_into_one(self):
        assert trigrams("aaaa") == {"  a", " aa", "aaa", "aa "}

    def test_yields_no_trigrams_without_word_characters(self):
        assert trigrams("") == set()
        assert trigrams("   ") == set()
        assert trigrams("---") == set()

    def test_passes_through_none(self):
        assert trigrams(None) is None

    def test_matches_pg_trgm_trigram_set(self):
        assert trigrams("Usage of estar") == {
            "  e", "  o", "  u", " es", " of", " us", "age",
            "ar ", "est", "ge ", "of ", "sag", "sta", "tar", "usa",
        }

    @pytest.mark.parametrize(
        "text, expected_count",
        PG_TRGM_TRIGRAM_COUNTS,
        ids=trigram_case_ids(),
    )
    def test_matches_pg_trgm_trigram_counts(self, text, expected_count):
        assert len(trigrams(text)) == expected_count


class TestSimilarity:
    @pytest.mark.parametrize(
        "left, right, expected",
        PG_TRGM_SIMILARITIES,
        ids=similarity_case_ids(),
    )
    def test_matches_pg_trgm(self, left, right, expected):
        assert similarity(left, right) == pytest.approx(
            expected, abs=FLOAT32_TOLERANCE
        )

    def test_is_symmetric(self):
        assert similarity("Usage of estar", "Ser vs. estar") == pytest.approx(
            similarity("Ser vs. estar", "Usage of estar")
        )

    def test_ignores_case(self):
        assert similarity("Present Tense", "present tense") == 1.0

    def test_ignores_punctuation(self):
        assert similarity("Present Tense -ar Verbs", "present tense ar verbs") == 1.0

    def test_ignores_whitespace(self):
        assert similarity("present   tense", "present tense") == 1.0

    def test_ignores_word_order(self):
        assert similarity("Ser vs. estar", "estar vs. Ser") == 1.0

    def test_scores_the_renamed_estar_pair_below_the_old_threshold(self):
        # The bug this stand-in was hiding: the old stand-in scored 0.3478 here,
        # clearing the 0.35 threshold, while production scored 0.272727 (the
        # first row of PG_TRGM_SIMILARITIES) and filtered the row out.
        assert similarity("Usage of estar", "Ser vs. estar") < 0.35

    def test_returns_none_when_either_side_is_none(self):
        assert similarity(None, "present tense") is None
        assert similarity("present tense", None) is None
        assert similarity(None, None) is None

    def test_returns_zero_without_trigrams_on_either_side(self):
        assert similarity("---", "present tense ar verbs") == 0.0
        assert similarity("present tense ar verbs", "---") == 0.0


@pytest.fixture()
def pg_trgm_similarity():
    """Query `similarity()` from the local Supabase Postgres.

    Opt in with PG_TRGM_LIVE_CHECK=1. Skips when that is unset, when Postgres
    is not running, or when the `pg_trgm` extension is missing.
    """
    if os.environ.get("PG_TRGM_LIVE_CHECK") != "1":
        pytest.skip("set PG_TRGM_LIVE_CHECK=1 to cross-check against pg_trgm")

    from database import engine

    try:
        with engine.connect() as connection:
            connection.execute(text("select similarity('a', 'b')")).scalar_one()
    except Exception as error:
        pytest.skip(f"local Postgres with pg_trgm is unavailable: {error}")

    def query(left, right):
        with engine.connect() as connection:
            return connection.execute(
                text("select similarity(:left, :right)"),
                {"left": left, "right": right},
            ).scalar_one()

    return query


class TestAgainstLivePostgres:
    """Cross-checks the stand-in against the local Supabase Postgres.

    Opt in with PG_TRGM_LIVE_CHECK=1; skipped when that is unset, when the
    database is unreachable, or when the `pg_trgm` extension is missing.
    """

    def test_agrees_with_pg_trgm_on_every_golden_pair(self, pg_trgm_similarity):
        for left, right, _expected in PG_TRGM_SIMILARITIES:
            live = pg_trgm_similarity(left, right)
            if live is None:
                continue

            assert similarity(left, right) == pytest.approx(
                live, abs=FLOAT32_TOLERANCE
            ), f"stand-in disagrees with pg_trgm on ({left!r}, {right!r})"

    def test_returns_none_where_pg_trgm_returns_null(self, pg_trgm_similarity):
        assert pg_trgm_similarity(None, "present tense") is None
        assert similarity(None, "present tense") is None