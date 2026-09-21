from graphs.llm import llm
from graphs.models import ProposedCatalogRules, CatalogRule
from graphs.prompts import propose_missing_rules_prompt
from graphs.states import RuleCreationAgentState
from models.canonical_rules import CanonicalRule
from crud.canonical_rules import get_missing_canonical_rules_for_pair

rule_proposer_llm = llm.with_structured_output(ProposedCatalogRules)

propose_rules_chain = propose_missing_rules_prompt | rule_proposer_llm

MAX_SUGGESTIONS = 5

NO_MISSING_RULES_MESSAGE = (
    "All rules in the catalog for this language pair have already been created. "
    "No missing rules to suggest."
)

def _format_candidates(candidates: list[CanonicalRule]) -> str:
    lines = []
    for entry in candidates:
        lines.append(
            "- id: {id}\n  name: {name}\n  description: {description}"
            .format(id=entry.id, name=entry.name, description=entry.description)
        )
    return "\n".join(lines)

def propose_rules_node(state: RuleCreationAgentState) -> RuleCreationAgentState:
    candidates = get_missing_canonical_rules_for_pair(
        state["db"],
        state["native_language_id"],
        state["target_language_id"],
    )
    if not candidates:
        return {
            **state,
            "proposed_rules": [],
            "message": NO_MISSING_RULES_MESSAGE,
        }

    result: ProposedCatalogRules = propose_rules_chain.invoke(
        {
            "native_language": state["native_language"],
            "target_language": state["target_language"],
            "candidates": _format_candidates(candidates),
        }
    )

    candidate_ids = {str(entry.id) for entry in candidates}
    order_by_id = {str(entry.id): index for index, entry in enumerate(candidates)}

    chosen = []
    picked_ids = set()
    for rule in result.rules:
        rule_id = str(rule.canonical_rule_id)
        if rule_id not in candidate_ids or rule_id in picked_ids:
            continue
        picked_ids.add(rule_id)
        chosen.append(rule)
    chosen.sort(key=lambda rule: order_by_id[str(rule.canonical_rule_id)])
    chosen = chosen[:MAX_SUGGESTIONS]

    return {
        **state,
        "proposed_rules": [rule.model_dump(mode="json") for rule in chosen],
        "message": "",
    }