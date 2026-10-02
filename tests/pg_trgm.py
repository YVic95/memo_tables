"""A faithful stand-in for Postgres `pg_trgm`'s `similarity()`, for SQLite.

SQLite has no `similarity()`, so `tests/conftest.py` registers
:func:`similarity` as a UDF and SQL predicates written against `pg_trgm` run
unchanged against the in-memory SQLite session.

`pg_trgm` lowercases, splits on every non-alphanumeric character, pads each
word with two leading spaces and one trailing space, takes the 3-grams of each
word without letting one span two words, and compares the two *sets* of
trigrams by their Jaccard index. Every part of that matters: the stand-in this
replaces lowercased but then took whole-string 3-grams and compared them with a
Dice coefficient, which put it on the other side of the retrieval threshold
from production and let a duplicate-detection false negative ship green.

`tests/test_pg_trgm.py` pins this against values measured from `pg_trgm` 1.6.
Run it with `PG_TRGM_LIVE_CHECK=1` to re-derive those values from the local
Supabase Postgres.
"""

import unicodedata

TRIGRAM_LENGTH = 3
LEADING_PADDING = "  "
TRAILING_PADDING = " "


def _is_word_character(character: str) -> bool:
    """Whether `character` belongs to a word rather than separating two of them.

    `pg_trgm` splits on everything that is not alphanumeric. Measured over
    every codepoint in the Basic Multilingual Plane, "letter, combining mark,
    decimal digit or Roman numeral letter" agrees with `pg_trgm` on all but
    fraction-style numerals (`²`) and half the combining marks. Neither rule is
    exact there, because `pg_trgm` classifies through the database locale's C
    library tables rather than through Unicode general categories; this one is
    the closer of the two and exact for everything a rule name can contain.
    """
    category = unicodedata.category(character)
    return category[0] in ("L", "M") or category in ("Nd", "Nl")


def _words(text: str):
    """Yield the maximal runs of word characters in `text`, lowercased."""
    word_characters: list[str] = []
    for character in text.lower():
        if _is_word_character(character):
            word_characters.append(character)
        elif word_characters:
            yield "".join(word_characters)
            word_characters = []
    if word_characters:
        yield "".join(word_characters)


def trigrams(text: str | None) -> set[str] | None:
    """The set of trigrams `pg_trgm` derives from `text`.

    Words shorter than a trigram survive because the padding is what supplies
    their trigrams: `"a"` still yields `{"  a", " a "}`.

    Returns None for None, so a NULL argument stays NULL the way Postgres does.
    """
    if text is None:
        return None

    extracted: set[str] = set()
    for word in _words(text):
        padded = f"{LEADING_PADDING}{word}{TRAILING_PADDING}"
        last_start = len(padded) - TRIGRAM_LENGTH
        for start in range(last_start + 1):
            extracted.add(padded[start : start + TRIGRAM_LENGTH])
    return extracted


def similarity(left: str | None, right: str | None) -> float | None:
    """How much the trigram sets of `left` and `right` overlap, in [0, 1].

    This is the Jaccard index of the two trigram sets, which is what
    `pg_trgm.similarity` computes, not a Dice coefficient. It returns 0.0 when
    neither side yields a trigram, and None when either side is NULL.
    """
    left_trigrams = trigrams(left)
    right_trigrams = trigrams(right)
    if left_trigrams is None or right_trigrams is None:
        return None

    combined = left_trigrams | right_trigrams
    if not combined:
        return 0.0
    return len(left_trigrams & right_trigrams) / len(combined)