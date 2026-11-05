import re

from langchain_core.runnables import RunnableLambda

from graphs.models import TableData, TableRow

NOUN_NUMBER_HEADERS = [
    "Singular",
    "Traducción",
    "Explicación",
    "Ejemplo",
    "Plural",
    "Traducción",
    "Explicación",
    "Ejemplo",
]

NOUN_GENDER_HEADERS = [
    "Masculino",
    "Traducción",
    "Explicación",
    "Ejemplo",
    "Femenino",
    "Traducción",
    "Explicación",
    "Ejemplo",
]

NOUN_NUMBER_TABLE = TableData(
    title="El número del sustantivo",
    headers=NOUN_NUMBER_HEADERS,
    rows=[
        TableRow(
            cells=[
                "la mesa",
                "the table",
                "Feminine; singular article 'la'",
                "La mesa es grande.",
                "las mesas",
                "the tables",
                "Plural adds -s",
                "Las mesas son grandes.",
            ]
        ),
        TableRow(
            cells=[
                "el libro",
                "the book",
                "Masculine; singular article 'el'",
                "El libro es nuevo.",
                "los libros",
                "the books",
                "Plural adds -s",
                "Los libros son nuevos.",
            ]
        ),
    ],
    noun_table_layout="noun_number",
)

NOUN_NUMBER_MULTI_TABLE = TableData(
    title="El número y el género del sustantivo",
    headers=NOUN_NUMBER_HEADERS,
    rows=[
        TableRow(
            cells=[
                "la mesa",
                "the table",
                "Feminine; singular article 'la'",
                "La mesa es grande.",
                "las mesas",
                "the tables",
                "Plural adds -s",
                "Las mesas son grandes.",
            ]
        ),
        TableRow(
            cells=[
                "el libro",
                "the book",
                "Masculine; singular article 'el'",
                "El libro es nuevo.",
                "los libros",
                "the books",
                "Plural adds -s",
                "Los libros son nuevos.",
            ]
        ),
        TableRow(
            cells=[
                "el problema",
                "the problem",
                "Masculine exception; ends in -ma",
                "El problema es difícil.",
                "los problemas",
                "the problems",
                "Plural adds -s",
                "Los problemas son difíciles.",
            ]
        ),
        TableRow(
            cells=[
                "la mano",
                "the hand",
                "Feminine exception; ends in -o",
                "La mano es pequeña.",
                "las manos",
                "the hands",
                "Plural adds -s",
                "Las manos son pequeñas.",
            ]
        ),
    ],
    noun_table_layout="noun_number",
)

NOUN_GENDER_TABLE = TableData(
    title="El género del sustantivo",
    headers=NOUN_GENDER_HEADERS,
    rows=[
        TableRow(
            cells=[
                "el libro",
                "the book",
                "Masculine; ends in -o",
                "El libro es nuevo.",
                "la mesa",
                "the table",
                "Feminine; ends in -a",
                "La mesa es grande.",
            ]
        ),
        TableRow(
            cells=[
                "el problema",
                "the problem",
                "Masculine exception; ends in -ma",
                "El problema es difícil.",
                "la mano",
                "the hand",
                "Feminine exception; ends in -o",
                "La mano es pequeña.",
            ]
        ),
    ],
    noun_table_layout="noun_gender",
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


class FakeNounLayoutLLM:
    """Stands in for the model's layout decision.

    Reads the rule name and description from the prompt and applies the same
    rule the prompt gives the model: a rule about number/plural gets the number
    layout, even when it also mentions gender; otherwise a gender rule gets the
    gender layout. Mixed rules return the multi-pattern number table.
    """

    def __init__(self):
        self.prompts: list[str] = []

    def with_structured_output(self, schema):
        def respond(prompt_value):
            prompt = prompt_value.to_string()
            self.prompts.append(prompt)
            rule_text = _rule_text(prompt).lower()
            is_number_rule = "plural" in rule_text or "number" in rule_text
            if is_number_rule and "gender" in rule_text:
                return NOUN_NUMBER_MULTI_TABLE
            if is_number_rule:
                return NOUN_NUMBER_TABLE
            return NOUN_GENDER_TABLE

        return RunnableLambda(respond)


def _rule_text(prompt: str) -> str:
    name = re.search(r"Rule name: (.*)", prompt)
    description = re.search(r"Rule description: (.*)", prompt)
    return " ".join(
        match.group(1) for match in (name, description) if match is not None
    )
