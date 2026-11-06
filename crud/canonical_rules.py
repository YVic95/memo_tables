import re
import uuid

from sqlalchemy import and_, exists, func, or_
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql.elements import ColumnElement
from models.canonical_rules import CanonicalRule
from models.grammar_rules import GrammarRule
from models.word_categories import WordCategory

CANONICAL_COVERAGE_SIMILARITY_THRESHOLD = 0.3

CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")

CANONICAL_RULE_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

def _has_faithful_linked_rule() -> ColumnElement[bool]:
    """Condition true for entries at least one linked rule actually teaches.

    Relation is many-to-one, an entry can carry several rules that
    between them cover only part of it — `ser-vs-estar` hanging off both
    `Usage of verb estar` and `Usage of verb ser` teaches neither verb on its own —
    so linkage alone is not enough to retire an entry.

    The rule is matched through an alias so the subquery gets its own FROM entry
    rather than binding to the outer query.
    """
    linked = aliased(GrammarRule)
    name_similarity = func.coalesce(
        func.similarity(linked.name, CanonicalRule.name), 0.0
    )
    return exists().where(
        and_(
            linked.canonical_rule_id == CanonicalRule.id,
            name_similarity >= CANONICAL_COVERAGE_SIMILARITY_THRESHOLD,
        )
    ).correlate(CanonicalRule)


def _pair_active_rules_query(
    db: Session,
    native_language_id: uuid.UUID,
    target_language_id: uuid.UUID,
):
    """Base query over a pair's active catalog entries, ordered by level then position."""
    return (
        db.query(CanonicalRule)
        .filter(
            CanonicalRule.native_language_id == native_language_id,
            CanonicalRule.target_language_id == target_language_id,
            CanonicalRule.is_active.is_(True),
        )
        .order_by(
            CanonicalRule.level.asc(),
            CanonicalRule.position.asc(),
        )
    )


def get_canonical_rules_for_pair(
    db: Session,
    native_language_id: uuid.UUID,
    target_language_id: uuid.UUID,
) -> list[CanonicalRule]:
    """Return the pair's active catalog entries, ordered by level then position."""
    return _pair_active_rules_query(
        db,
        native_language_id,
        target_language_id,
    ).all()


VALID_CANONICAL_SORTS = ("level", "category", "status", "name")
VALID_CANONICAL_SORT_DIRS = ("asc", "desc")


def _normalize_canonical_level(level: str | None) -> str | None:
    if not level:
        return None
    normalized = level.strip().upper()
    return normalized if normalized in CEFR_LEVELS else None


def _normalize_canonical_status(status: str | None) -> bool | None:
    if not status:
        return None
    normalized = status.strip().lower()
    if normalized == "all":
        return None
    if normalized == "active":
        return True
    if normalized == "inactive":
        return False
    return None


def _normalize_canonical_category(category: str | None) -> str | None:
    if not category:
        return None
    normalized = category.strip()
    return normalized or None


def _normalize_canonical_sort(
    sort: str | None, direction: str | None
) -> tuple[str | None, str]:
    if not sort:
        return None, "asc"
    normalized_sort = sort.strip().lower()
    if normalized_sort not in VALID_CANONICAL_SORTS:
        return None, "asc"
    normalized_dir = (direction or "asc").strip().lower()
    if normalized_dir not in VALID_CANONICAL_SORT_DIRS:
        normalized_dir = "asc"
    return normalized_sort, normalized_dir


def get_all_canonical_rules_for_pair(
    db: Session,
    native_language_id: uuid.UUID,
    target_language_id: uuid.UUID,
    *,
    level: str | None = None,
    category: str | None = None,
    status: str | None = None,
    sort: str | None = None,
    direction: str | None = None,
) -> list[dict]:
    """
        Return the pair's full catalog — active and inactive — ordered by level then position.

        Optional filters: `level` (A1..C2, invalid ignored), `category`
        (WordCategory slug or name, invalid ignored by yielding no rows),
        `status` (`active`/`inactive`/`all`, invalid ignored).
        Optional `sort` (`level`/`category`/`status`/`name`) with `direction`
        (`asc`/`desc`) overrides the default ordering; invalid sort falls back
        to the default. `position ASC` is always the final tiebreak.
    """
    level_filter = _normalize_canonical_level(level)
    status_filter = _normalize_canonical_status(status)
    category_filter = _normalize_canonical_category(category)
    sort_by, sort_dir = _normalize_canonical_sort(sort, direction)
    descending = sort_dir == "desc"

    def _order(column):
        return column.desc() if descending else column.asc()

    query = (
        db.query(CanonicalRule, WordCategory.name)
        .join(WordCategory, WordCategory.id == CanonicalRule.word_category_id)
        .filter(
            CanonicalRule.native_language_id == native_language_id,
            CanonicalRule.target_language_id == target_language_id,
        )
    )
    if level_filter is not None:
        query = query.filter(CanonicalRule.level == level_filter)
    if status_filter is not None:
        query = query.filter(CanonicalRule.is_active.is_(status_filter))
    if category_filter is not None:
        lowered = category_filter.lower()
        query = query.filter(
            or_(
                func.lower(WordCategory.slug) == lowered,
                func.lower(WordCategory.name) == lowered,
            )
        )
    if sort_by == "level":
        query = query.order_by(
            _order(CanonicalRule.level), CanonicalRule.position.asc()
        )
    elif sort_by == "category":
        query = query.order_by(
            _order(func.lower(WordCategory.name)), CanonicalRule.position.asc()
        )
    elif sort_by == "status":
        query = query.order_by(
            _order(CanonicalRule.is_active), CanonicalRule.position.asc()
        )
    elif sort_by == "name":
        query = query.order_by(
            _order(func.lower(CanonicalRule.name)), CanonicalRule.position.asc()
        )
    else:
        query = query.order_by(
            CanonicalRule.level.asc(),
            CanonicalRule.position.asc(),
        )
    rows = query.all()
    return [
        {
            "id": rule.id,
            "name": rule.name,
            "slug": rule.slug,
            "level": rule.level,
            "position": rule.position,
            "category_name": category_name,
            "is_active": rule.is_active,
        }
        for rule, category_name in rows
    ]

def _validate_rule_fields(
    db: Session,
    *,
    native_language_id: uuid.UUID,
    target_language_id: uuid.UUID,
    word_category_id: uuid.UUID,
    level: str,
    slug: str,
    exclude_rule_id: uuid.UUID | None = None,
) -> tuple[str, str]:
    """
        Validate editable rule fields, returning the normalized (level, slug).
    """
    level = level.strip()
    if level not in CEFR_LEVELS:
        raise ValueError("Level must be one of A1, A2, B1, B2, C1, C2")

    slug = slug.strip().lower()
    if not CANONICAL_RULE_SLUG_PATTERN.match(slug):
        raise ValueError(
            "Slug must contain only lowercase letters, digits, and single "
            "hyphens between them (e.g. present-tense)"
        )

    existing = get_canonical_rule_by_slug(
        db, native_language_id, target_language_id, slug
    )
    if existing is not None and existing.id != exclude_rule_id:
        raise ValueError(
            "A rule with this slug already exists for this language pair"
        )

    category_exists = (
        db.query(WordCategory.id)
        .filter(WordCategory.id == word_category_id)
        .first()
        is not None
    )
    if not category_exists:
        raise ValueError("Selected word category does not exist")

    return level, slug


def create_canonical_rule(
    db: Session,
    *,
    native_language_id: uuid.UUID,
    target_language_id: uuid.UUID,
    word_category_id: uuid.UUID,
    level: str,
    name: str,
    description: str,
    slug: str,
) -> CanonicalRule:
    """
        Create an active catalog entry for the pair
    """
    level, slug = _validate_rule_fields(
        db,
        native_language_id=native_language_id,
        target_language_id=target_language_id,
        word_category_id=word_category_id,
        level=level,
        slug=slug,
    )

    last_position = (
        db.query(func.max(CanonicalRule.position))
        .filter(
            CanonicalRule.native_language_id == native_language_id,
            CanonicalRule.target_language_id == target_language_id,
            CanonicalRule.level == level,
        )
        .scalar()
    )

    rule = CanonicalRule(
        native_language_id=native_language_id,
        target_language_id=target_language_id,
        word_category_id=word_category_id,
        level=level,
        name=name.strip(),
        description=description.strip(),
        position=(last_position or 0) + 1,
        slug=slug,
        is_active=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

def get_missing_canonical_rules_for_pair(
    db: Session,
    native_language_id: uuid.UUID,
    target_language_id: uuid.UUID,
) -> list[CanonicalRule]:
    """Return the pair's active catalog entries not yet taught by a rule.

    An entry is missing when no linked rule is a faithful copy of it, matched on
    name alone for the reason given on `CANONICAL_COVERAGE_SIMILARITY_THRESHOLD`.
    Ordered by level then position so a proposal surfaced from this list is
    pedagogically ordered.
    """
    return (
        _pair_active_rules_query(db, native_language_id, target_language_id)
        .filter(~_has_faithful_linked_rule())
        .all()
    )

def get_canonical_rule_by_id(
    db: Session,
    rule_id: uuid.UUID,
) -> CanonicalRule | None:
    return db.query(CanonicalRule).filter(CanonicalRule.id == rule_id).first()


def is_canonical_rule_linked(db: Session, rule_id: uuid.UUID) -> bool:
    """Return True if any grammar rule references this canonical rule."""
    return (
        db.query(GrammarRule.id)
        .filter(GrammarRule.canonical_rule_id == rule_id)
        .first()
        is not None
    )


def get_linked_canonical_rule_ids(
    db: Session, rule_ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    if not rule_ids:
        return set()
    rows = (
        db.query(GrammarRule.canonical_rule_id)
        .filter(GrammarRule.canonical_rule_id.in_(rule_ids))
        .distinct()
        .all()
    )
    return {row[0] for row in rows}


def set_canonical_rule_active(
    db: Session, rule_id: uuid.UUID, is_active: bool
) -> CanonicalRule | None:
    rule = get_canonical_rule_by_id(db, rule_id)
    if rule is None:
        return None
    rule.is_active = bool(is_active)
    db.commit()
    db.refresh(rule)
    return rule


def update_canonical_rule(
    db: Session,
    *,
    rule_id: uuid.UUID,
    word_category_id: uuid.UUID,
    level: str,
    name: str,
    description: str,
    slug: str,
) -> CanonicalRule | None:

    rule = get_canonical_rule_by_id(db, rule_id)
    if rule is None:
        return None

    level, slug = _validate_rule_fields(
        db,
        native_language_id=rule.native_language_id,
        target_language_id=rule.target_language_id,
        word_category_id=word_category_id,
        level=level,
        slug=slug,
        exclude_rule_id=rule.id,
    )

    rule.word_category_id = word_category_id
    rule.level = level
    rule.name = name.strip()
    rule.description = description.strip()
    rule.slug = slug
    db.commit()
    db.refresh(rule)
    return rule


def get_canonical_rule_by_slug(
    db: Session,
    native_language_id: uuid.UUID,
    target_language_id: uuid.UUID,
    slug: str,
) -> CanonicalRule | None:
    return (
        db.query(CanonicalRule)
        .filter(
            CanonicalRule.native_language_id == native_language_id,
            CanonicalRule.target_language_id == target_language_id,
            CanonicalRule.slug == slug,
        )
        .first()
    )


