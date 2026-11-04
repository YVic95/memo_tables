"""Deterministic normalization helpers for noun forms.

The deduction model decides which noun each surface form belongs to, but the
grouping keys and citation-form choice are normalized here so a model that
returns one base word per surface form cannot split a single noun into
multiple vocabulary entries.
"""

_ARTICLE_RULES = {
    "spanish": {
        "articles": frozenset({"el", "la", "los", "las", "un", "una", "unos", "unas"}),
        "singular_definite": {
            "el": "el",
            "la": "la",
            "los": "el",
            "las": "la",
            "un": "el",
            "una": "la",
            "unos": "el",
            "unas": "la",
        },
        "plural_by_suffix": False,
    },
    "english": {
        "articles": frozenset({"the", "a", "an"}),
        "singular_definite": {"the": "the", "a": "the", "an": "the"},
        "plural_by_suffix": True,
    },
}


def _article_rules(language_name: str) -> dict | None:
    return _ARTICLE_RULES.get(language_name.strip().lower())


def _words(text: str) -> list[str]:
    return text.lower().strip().split()


def _strip_article(words: list[str], rules: dict | None) -> list[str]:
    if rules and len(words) > 1 and words[0] in rules["articles"]:
        return words[1:]
    return words


def _singular_variants(words: list[str]) -> list[list[str]]:
    """Return singular candidates, most likely first.

    Both suffixes are kept because ``-es`` is ambiguous: "mesas" strips to
    "mesa", while "flores" strips to "flor". Grouping tests every candidate.
    """
    if not words:
        return []

    last_word = words[-1]
    if not last_word.endswith("s"):
        return [words]

    variants = [words[:-1] + [last_word[:-1]]]
    if last_word.endswith("es") and len(last_word) > 3:
        variants.append(words[:-1] + [last_word[:-2]])
    return variants


def noun_keys(text: str, language_name: str) -> set[str]:
    """Return the plausible normalized keys for a noun phrase."""
    rules = _article_rules(language_name)
    words = _strip_article(_words(text), rules)

    return {
        " ".join(variant)
        for variant in _singular_variants(words)
    }


def singular_form(text: str, language_name: str) -> str:
    variants = _singular_variants(_words(text))
    return " ".join(variants[0]) if variants else text.lower().strip()


def is_singular_definite(text: str, language_name: str) -> bool:
    words = _words(text)
    rules = _article_rules(language_name)
    if not words or not rules:
        return False

    if words[0] not in rules["singular_definite"].values():
        return False
    if rules["plural_by_suffix"] and words[-1].endswith("s"):
        return False

    return True


def citation_candidates(text: str, language_name: str) -> list[tuple[int, str]]:
    """Return ``(priority, citation)`` pairs, best candidate first."""
    words = _words(text)
    rules = _article_rules(language_name)
    if not rules or len(words) < 2 or words[0] not in rules["singular_definite"]:
        return []

    candidates = []
    for index, variant in enumerate(_singular_variants(words)):
        variant = list(variant)
        variant[0] = rules["singular_definite"][words[0]]
        candidates.append((index, " ".join(variant)))

    return candidates


def citation_form(text: str, language_name: str) -> str | None:
    """Return the best singular definite-article form, or None when there is no article."""
    candidates = citation_candidates(text, language_name)
    if not candidates:
        return None

    return min(candidates)[1]
