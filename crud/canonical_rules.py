import uuid
from sqlalchemy.orm import Session
from models.canonical_rules import CanonicalRule
from models.grammar_rules import GrammarRule


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
    """Return the pair's active catalog entries not yet linked to a persisted rule.

    An entry is missing when no grammar_rules row links to it. Ordered by level
    then position so a proposal surfaced from this list is pedagogically ordered.
    """
    return (
        _pair_active_rules_query(db, native_language_id, target_language_id)
        .outerjoin(
            GrammarRule,
            GrammarRule.canonical_rule_id == CanonicalRule.id,
        )
        .filter(GrammarRule.id.is_(None))
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