import logging
import uuid
from dataclasses import dataclass
from typing import cast

from sqlalchemy import func
from sqlalchemy.orm import Session

from graphs.llm import llm
from graphs.models import DuplicateCheckResult, DuplicateJudgeResult, ExistingRule
from graphs.prompts import duplicate_check_prompt
from models.canonical_rules import CanonicalRule
from models.grammar_rules import GrammarRule

logger = logging.getLogger(__name__)

TRIGRAM_SIMILARITY_THRESHOLD = 0.35
MAX_CANDIDATES = 5

judge_llm = llm.with_structured_output(DuplicateJudgeResult)
judge_chain = duplicate_check_prompt | judge_llm


@dataclass
class SimilarRuleCandidate:
    id: uuid.UUID
    name: str
    description: str | None
    catalog_name: str


def get_similar_rule_candidates(
    db: Session,
    *,
    target_language_id: uuid.UUID,
    name: str,
) -> list[SimilarRuleCandidate]:
    if not name.strip():
        return []

    similarity = func.similarity(GrammarRule.name, name)
    rows = (
        db.query(GrammarRule, CanonicalRule.name)
        .join(CanonicalRule, GrammarRule.canonical_rule_id == CanonicalRule.id)
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
            catalog_name=catalog_name,
        )
        for rule, catalog_name in rows
    ]

def _format_candidates(candidates: list[SimilarRuleCandidate]) -> str:
    return "\n".join(
        f"- id: {candidate.id}\n"
        f"  name: {candidate.name}\n"
        f"  catalog name: {candidate.catalog_name}\n"
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
    )
    if not candidates:
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
