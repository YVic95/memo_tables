import uuid

from sqlalchemy import and_, exists, func
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql.elements import ColumnElement
from models.canonical_rules import CanonicalRule
from models.grammar_rules import GrammarRule

CANONICAL_COVERAGE_SIMILARITY_THRESHOLD = 0.3

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


def upsert_canonical_rule(
    db: Session,
    *,
    native_language_id: uuid.UUID,
    target_language_id: uuid.UUID,
    word_category_id: uuid.UUID,
    level: str,
    name: str,
    description: str,
    position: int,
    slug: str,
) -> CanonicalRule:
    """Upsert by pair+slug and return the rule.

    Flushes but does not commit; the caller owns the transaction boundary.
    """
    rule = get_canonical_rule_by_slug(
        db,
        native_language_id=native_language_id,
        target_language_id=target_language_id,
        slug=slug,
    )
    if rule is None:
        rule = CanonicalRule(
            native_language_id=native_language_id,
            target_language_id=target_language_id,
            word_category_id=word_category_id,
            level=level,
            name=name,
            description=description,
            position=position,
            slug=slug,
            is_active=True,
        )
        db.add(rule)
    else:
        rule.word_category_id = word_category_id
        rule.level = level
        rule.name = name
        rule.description = description
        rule.position = position
        rule.is_active = True
    db.flush()
    db.refresh(rule)
    return rule


def deactivate_canonical_rules_not_in(
    db: Session,
    native_language_id: uuid.UUID,
    target_language_id: uuid.UUID,
    active_slugs: set[str],
) -> None:
    """Soft-deactivate active canonical rules in the pair whose slug is not in active_slugs.

    Rows are never hard-deleted. An empty active_slugs deactivates every
    active rule in the pair — that is the correct semantics for a catalog
    file whose rules list is empty (the file is still the source of truth).

    Flushes but does not commit; the caller owns the transaction boundary.
    """
    rules_to_deactivate = (
        db.query(CanonicalRule)
        .filter(
            CanonicalRule.native_language_id == native_language_id,
            CanonicalRule.target_language_id == target_language_id,
            CanonicalRule.is_active.is_(True),
            ~CanonicalRule.slug.in_(active_slugs),
        )
        .all()
    )
    for rule in rules_to_deactivate:
        rule.is_active = False
        db.add(rule)
    db.flush()