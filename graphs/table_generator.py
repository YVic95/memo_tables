from langchain_core.prompts import BasePromptTemplate

from graphs.category_table_config import (
    CategoryConfig,
)
from graphs.llm import llm
from graphs.models import AdjectiveTableLayoutClassification, TableData
from graphs.states import GenerateTableState


def _invoke_table_prompt(
    prompt: BasePromptTemplate,
    state: GenerateTableState,
    additional_prompt_variables: dict[str, str] | None = None,
) -> TableData:
    chain = prompt | llm.with_structured_output(TableData)
    return chain.invoke({
        "native_language": state["native_language"],
        "target_language": state["target_language"],
        "rule_name": state["rule_name"],
        "rule_description": state["rule_description"] or "",
        **(additional_prompt_variables or {}),
    })


def _invoke_classifier(
    prompt: BasePromptTemplate,
    state: GenerateTableState,
    classifier_input=None,
) -> str:
    chain = prompt | llm.with_structured_output(AdjectiveTableLayoutClassification)
    variables = (
        classifier_input(state)
        if classifier_input is not None
        else {
            "rule_name": state.get("rule_name") or "",
            "rule_description": state.get("rule_description") or "",
        }
    )
    result = chain.invoke(variables)
    layout = result.adjective_table_layout
    return layout.value if hasattr(layout, "value") else str(layout)


def _require_layout_match(table: TableData, expected_layout: str) -> None:
    actual = table.adjective_table_layout
    actual_value = actual.value if hasattr(actual, "value") else (
        str(actual) if actual is not None else None
    )
    if actual_value != expected_layout:
        raise ValueError(
            f"Generator layout mismatch: classifier chose {expected_layout} "
            f"but generated {actual_value}"
        )


def _apply_adjective_titles(
    tables: list[TableData], state: GenerateTableState
) -> None:
    """Enforce general-table title rules for adjective layouts.

    Number-only / gender-only generals use the rule name verbatim;
    agreement generals derive "<rule> by number" / "<rule> by gender".
    Other-rule tables keep the model's title.
    """
    if state.get("word_category_slug") != "adjective":
        return
    rule_name = (state.get("rule_name") or "").strip()
    if not rule_name:
        return
    for table in tables:
        layout = table.adjective_table_layout
        value = layout.value if hasattr(layout, "value") else str(layout)
        if value == "adj_number" or value == "adj_gender":
            table.title = rule_name
        elif value == "adj_agreement_number":
            table.title = f"{rule_name} by number"
        elif value == "adj_agreement_gender":
            table.title = f"{rule_name} by gender"


def _generate_from_classifier(
    state: GenerateTableState, config: CategoryConfig
) -> tuple[TableData, ...]:
    if config.classifier_prompt is None:
        raise ValueError("Category configuration has no classifier prompt")
    layout = _invoke_classifier(
        config.classifier_prompt, state, config.classifier_input
    )
    # Robustness: if the model returns a table layout instead of the
    # agreement signal, route it to the agreement pair all the same.
    if layout in ("adj_agreement_number", "adj_agreement_gender"):
        layout = "adj_agreement"
    route = config.layout_routes.get(str(layout))
    if route is None:
        raise ValueError(f"No generation route configured for table layout: {layout}")

    if route.prompt_role is None:
        raise ValueError("Category prompt roles require a prompt role")
    prompt = config.prompt_roles[route.prompt_role]

    additional_prompt_variables: dict[str, str] = {}
    # The shared gender-or-agreement prompt always takes {avoid_phrases}:
    # the standalone gender-only use passes an empty list.
    if (
        route.prompt_role == "gender_or_agreement"
        and route.companion_prompt_role is None
    ):
        additional_prompt_variables = {"avoid_phrases": ""}
    entry_table = _invoke_table_prompt(prompt, state, additional_prompt_variables)

    if route.validator is not None:
        route.validator(entry_table)
    elif config.layout_validator is not None:
        config.layout_validator(entry_table)
    _require_layout_match(entry_table, route.entry_layout or str(layout))

    tables = [entry_table]
    if route.companion_prompt_role is not None:
        companion_variables: dict[str, str] = {}
        if route.companion_context is not None:
            companion_variables = route.companion_context(entry_table)
        companion_prompt = config.prompt_roles[route.companion_prompt_role]
        companion_table = _invoke_table_prompt(
            companion_prompt, state, companion_variables
        )
        (route.companion_validator or route.validator)(companion_table)
        expected_companion = route.companion_layout or str(layout)
        _require_layout_match(companion_table, expected_companion)
        tables.append(companion_table)
    _apply_adjective_titles(tables, state)
    return tuple(tables)


def _generate_from_prompt_roles(
    state: GenerateTableState, config: CategoryConfig
) -> tuple[TableData, ...]:
    if config.entry_prompt_role is None:
        raise ValueError("Category prompt roles require an entry prompt role")
    entry_table = _invoke_table_prompt(
        config.prompt_roles[config.entry_prompt_role], state
    )

    if config.layout_field is None:
        raise ValueError("Category prompt roles require a layout field")
    layout = getattr(entry_table, config.layout_field)
    route = config.layout_routes.get(str(layout))
    if route is None:
        if config.layout_validator is not None:
            config.layout_validator(entry_table)
        raise ValueError(f"No generation route configured for table layout: {layout}")

    if route.validator is not None:
        route.validator(entry_table)
    tables = [entry_table]
    if route.companion_prompt_role is not None:
        additional_prompt_variables: dict[str, str] = {}
        if route.companion_context is not None:
            additional_prompt_variables = route.companion_context(entry_table)
        companion_prompt = config.prompt_roles[route.companion_prompt_role]
        companion_table = _invoke_table_prompt(
            companion_prompt, state, additional_prompt_variables
        )
        (route.companion_validator or route.validator)(companion_table)
        tables.append(companion_table)
    return tuple(tables)


def _generate_tables(
    state: GenerateTableState, config: CategoryConfig
) -> tuple[TableData, ...]:
    if config.prompt is not None:
        table = _invoke_table_prompt(config.prompt, state)
        if config.validator is not None:
            config.validator(table)
        return (table,)
    if config.classifier_prompt is not None:
        return _generate_from_classifier(state, config)
    if config.prompt_roles:
        return _generate_from_prompt_roles(state, config)
    raise ValueError("Category configuration has no prompt")
