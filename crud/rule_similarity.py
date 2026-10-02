import logging
import uuid
from dataclasses import dataclass
from typing import cast

from sqlalchemy import func, literal
from sqlalchemy.orm import Session

from graphs.llm import llm
from graphs.models import DuplicateCheckResult, DuplicateJudgeResult, ExistingRule
from graphs.prompts import duplicate_check_prompt
from models.grammar_rules import GrammarRule

logger = logging.getLogger(__name__)

TRIGRAM_SIMILARITY_THRESHOLD = 0.2
MAX_CANDIDATES = 5

judge_llm = llm.with_structured_output(DuplicateJudgeResult)
judge_chain = duplicate_check_prompt | judge_llm


@dataclass
class SimilarRuleCandidate:
    id: uuid.UUID
    name: str
    description: str | None


def _similarity_or_zero(column, text: str):
    """Trigram similarity of `column` against `text`, as a number, never NULL.

    Postgres' `similarity()` is NULL when either argument is, and a NULL
    description is ordinary here, so the score is collapsed to zero rather than
    left to the surrounding expression. `greatest()` already ignores NULLs, so on
    the current shape this is belt and braces rather than load-bearing: it keeps
    the query correct for a NULL description even if the combining function ever
    changes to one that propagates NULL, which would silently filter every row
    out instead of scoring it on its name.

    A blank proposal field contributes no signal at all, rather than an
    empty-string comparison.
    """
    if not text.strip():
        return literal(0.0)
    return func.coalesce(func.similarity(column, text), 0.0)


def _similarity_to_proposal(*, name: str, description: str):
    """How close a stored rule is to the proposal, matching field to field.

    A rule's name is compared against the proposed title and its description
    against the proposed explanation, so a rule counts as retrieved when either
    field is close enough. Descriptions are the signal that survives a rule being
    renamed: `similarity('Permanent vs. temporary descriptions', 'Ser vs. estar')`
    is 0.0652, under the threshold, while the two descriptions score 1.0.

    Only text `grammar_rules` itself stores takes part. The catalog entry's name
    is deliberately not joined in. Where a rule's own name has been edited away
    from its catalog entry the two disagree about what the rule teaches —
    `Usage of estar` against a catalog entry named `Present tense regular -ar
    conjugation` scores 0.02, nowhere near the retrieval threshold — and handing
    the judge both at once let the stale one veto a real duplicate. Since #44
    made the relation many-to-one, `canonical_rules.name` names the entry rather
    than any one of the rules hanging off it, so it is not a candidate identifier
    to begin with.
    """
    return func.greatest(
        _similarity_or_zero(GrammarRule.name, name),
        _similarity_or_zero(GrammarRule.description, description),
    )


def get_similar_rule_candidates(
    db: Session,
    *,
    target_language_id: uuid.UUID,
    name: str,
    description: str,
) -> list[SimilarRuleCandidate]:
    if not name.strip() and not description.strip():
        return []

    similarity = _similarity_to_proposal(name=name, description=description)
    rows = (
        db.query(GrammarRule)
        .filter(
            GrammarRule.language_id == target_language_id,
            similarity >= TRIGRAM_SIMILARITY_THRESHOLD,
        )
        .order_by(similarity.desc())
        .limit(MAX_CANDIDATES)
        .all()
    )
    return [
        SimilarRuleCandidate(
            id=rule.id,
            name=rule.name,
            description=rule.description,
        )
        for rule in rows
    ]


def _format_candidates(candidates: list[SimilarRuleCandidate]) -> str:
    return "\n".join(
        f"- id: {candidate.id}\n"
        f"  name: {candidate.name}\n"
        f"  description: {candidate.description or ''}"
        for candidate in candidates
    )


def check_similar_rules(
    db: Session,
    *,
    target_language_id: uuid.UUID,
    proposed_title: str,
    proposed_description: str,
) -> DuplicateCheckResult:
    not_similar = DuplicateCheckResult(similar=False, existing_rule=None)

    candidates = get_similar_rule_candidates(
        db,
        target_language_id=target_language_id,
        name=proposed_title,
        description=proposed_description,
    )
    if not candidates:
        logger.info(
            "Duplicate check for %r: nothing cleared the %s retrieval threshold",
            proposed_title,
            TRIGRAM_SIMILARITY_THRESHOLD,
        )
        return not_similar

    try:
        verdict = cast(
            DuplicateJudgeResult,
            judge_chain.invoke(
                {
                    "rule_title": proposed_title,
                    "rule_explanation": proposed_description,
                    "candidates": _format_candidates(candidates),
                }
            ),
        )
    except Exception:
        logger.exception("Duplicate check LLM call failed")
        return not_similar

    logger.info(
        "Duplicate check for %r against %d candidate(s) [%s]: similar=%s best_match_id=%s",
        proposed_title,
        len(candidates),
        ", ".join(f"{candidate.name!r} ({candidate.id})" for candidate in candidates),
        verdict.similar,
        verdict.best_match_id,
    )

    if not verdict.similar or verdict.best_match_id is None:
        return not_similar

    match = next(
        (candidate for candidate in candidates if candidate.id == verdict.best_match_id),
        None,
    )
    if match is None:
        logger.warning(
            "Judge returned unknown best_match_id: %s", verdict.best_match_id
        )
        return not_similar

    return DuplicateCheckResult(
        similar=True,
        existing_rule=ExistingRule(
            id=match.id,
            name=match.name,
            description=match.description,
        ),
    )
