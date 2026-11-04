from langchain_core.runnables import RunnableLambda

from graphs.models import TableData, TableRow

NOUN_TABLE = TableData(
    title="El sustantivo",
    headers=["Sustantivo", "Explicación", "Ejemplo"],
    rows=[
        TableRow(cells=["la mesa", "Feminine; plural adds -s", "La mesa es grande"]),
        TableRow(cells=["las mesas", "Feminine; plural adds -s", "Las mesas son grandes"]),
    ],
)

PROMPT_VARIABLES = {
    "native_language": "English",
    "target_language": "Spanish",
    "rule_name": "Noun Gender",
    "rule_description": "Masculine vs feminine",
}


class FakeStructuredLLM:
    def __init__(self, result):
        self.result = result
        self.prompts: list[str] = []

    def with_structured_output(self, schema):
        def respond(prompt_value):
            self.prompts.append(prompt_value.to_string())
            return self.result

        return RunnableLambda(respond)
