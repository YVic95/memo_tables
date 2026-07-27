import json
from graphs.llm import llm
from graphs.models import FragmentationOutput
from graphs.prompts import fragmentation_prompt
from graphs.states import GenerateTableState

fragmentation_llm = llm.with_structured_output(FragmentationOutput)
fragmentation_chain = fragmentation_prompt | fragmentation_llm

def generate_fragmented_tables_node(state: GenerateTableState) -> GenerateTableState:
    result: FragmentationOutput = fragmentation_chain.invoke({
        "general_table_json": json.dumps(state["general_table"], indent=2),
    })

    return {
        **state,
        "should_fragment": result.should_fragment,
        "fragmented_tables": [t.model_dump() for t in result.tables],
    }
