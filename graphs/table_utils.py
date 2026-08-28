import re

COLUMN_ROLES = {
    "verb": {0: "label", 1: "form", 2: "example", 3: "explanation"},
}
DEFAULT_COLUMN_ROLES = {0: "label", 1: "explanation", 2: "example"}


def column_roles(word_category_slug: str) -> dict[int, str]:
    return COLUMN_ROLES.get(word_category_slug, DEFAULT_COLUMN_ROLES)


def role_to_column(roles: dict[int, str]) -> dict[str, int]:
    return {role: index for index, role in roles.items()}


def cell_at_role(cells: list[str], role_lookup: dict[str, int], role: str) -> str | None:
    column = role_lookup.get(role)
    if column is None or column >= len(cells):
        return None
    return cells[column]


def tokenize_words(text: str) -> list[str]:
    return [word for word in re.findall(r"[\w']+", text)]