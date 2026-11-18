from graphs.category_table_config import CATEGORY_CONFIG, CategoryConfig
from graphs.prompts import generate_table_prompt
from graphs.states import GenerateTableState
from graphs.table_generator import _generate_tables


def generate_category_table_node(state: GenerateTableState) -> GenerateTableState:
    slug = state.get("word_category_slug")
    config = CATEGORY_CONFIG.get(slug)
    if config is None:
        config = CategoryConfig(prompt=generate_table_prompt)

    tables = _generate_tables(state, config)
    return {
        **state,
        "general_tables": [table.model_dump() for table in tables],
    }
