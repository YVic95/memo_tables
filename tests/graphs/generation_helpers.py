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

ADJ_NUMBER_HEADERS = [
    "Singular",
    "Traducción",
    "Explicación",
    "Ejemplo",
    "Plural",
    "Traducción",
    "Explicación",
    "Ejemplo",
]

ADJ_GENDER_HEADERS = [
    "Masculino",
    "Traducción",
    "Explicación",
    "Ejemplo",
    "Femenino",
    "Traducción",
    "Explicación",
    "Ejemplo",
]

ADJ_NUMBER_TABLE = TableData(
    title="El número del adjetivo",
    headers=ADJ_NUMBER_HEADERS,
    rows=[
        TableRow(
            cells=[
                "el libro *rojo*",
                "the red book",
                "Masculine; singular article 'el'",
                "El libro rojo es nuevo.",
                "los libros *rojos*",
                "the red books",
                "Plural adds -s to the noun and the adjective",
                "Los libros rojos son nuevos.",
            ]
        ),
        TableRow(
            cells=[
                "el dólar *fuerte*",
                "the strong dollar",
                "Masculine; singular article 'el'",
                "El dólar fuerte sube.",
                "los dólares *fuertes*",
                "the strong dollars",
                "Plural adds -es to nouns and adjectives ending in a consonant",
                "Los dólares fuertes suben.",
            ]
        ),
    ],
    adjective_table_layout="adj_number",
)

ADJ_GENDER_TABLE = TableData(
    title="El género del adjetivo",
    headers=ADJ_GENDER_HEADERS,
    rows=[
        TableRow(
            cells=[
                "el chico *alto*",
                "the tall boy",
                "Masculine; adjective ends in -o",
                "El chico alto corre.",
                "la chica *alta*",
                "the tall girl",
                "Feminine; adjective ends in -a",
                "La chica alta corre.",
            ]
        ),
        TableRow(
            cells=[
                "el libro *bueno*",
                "the good book",
                "Masculine; adjective ends in -o",
                "El libro bueno es caro.",
                "la mesa *buena*",
                "the good table",
                "Feminine; adjective ends in -a",
                "La mesa buena es cara.",
            ]
        ),
    ],
    adjective_table_layout="adj_gender",
)

ADJ_AGREEMENT_HEADERS = [
    "Masculino",
    "Traducción",
    "Explicación",
    "Ejemplo",
    "Femenino",
    "Traducción",
    "Explicación",
    "Ejemplo",
]

ADJ_AGREEMENT_NUMBER_TABLE = TableData(
    title="La concordancia del adjetivo by number",
    headers=ADJ_NUMBER_HEADERS,
    rows=[
        TableRow(
            cells=[
                "el coche *azul*",
                "the blue car",
                "Masculine singular: noun and adjective agree",
                "El coche azul es nuevo.",
                "los coches *azules*",
                "the blue cars",
                "Masculine plural: noun and adjective agree",
                "Los coches azules son nuevos.",
            ]
        ),
        TableRow(
            cells=[
                "el árbol *verde*",
                "the green tree",
                "Masculine singular: noun and adjective agree",
                "El árbol verde es alto.",
                "los árboles *verdes*",
                "the green trees",
                "Masculine plural: noun and adjective agree",
                "Los árboles verdes son altos.",
            ]
        ),
    ],
    adjective_table_layout="adj_agreement_number",
)

ADJ_AGREEMENT_TABLE = TableData(
    title="La concordancia del adjetivo",
    headers=ADJ_AGREEMENT_HEADERS,
    rows=[
        TableRow(
            cells=[
                "el libro *rojo*",
                "the red book",
                "Masculine singular: noun and adjective agree",
                "El libro rojo es nuevo.",
                "la mesa *roja*",
                "the red table",
                "Feminine singular: noun and adjective agree",
                "La mesa roja es grande.",
            ]
        ),
        TableRow(
            cells=[
                "los chicos *altos*",
                "the tall boys",
                "Masculine plural: noun and adjective agree",
                "Los chicos altos corren.",
                "las chicas *altas*",
                "the tall girls",
                "Feminine plural: noun and adjective agree",
                "Las chicas altas corren.",
            ]
        ),
    ],
    adjective_table_layout="adj_agreement_gender",
)

ADJ_OTHER_HEADERS = [
    "Adjetivo",
    "Traducción",
    "Explicación",
    "Ejemplo",
]

ADJ_OTHER_TABLE = TableData(
    title="Los demostrativos",
    headers=ADJ_OTHER_HEADERS,
    rows=[
        TableRow(
            cells=[
                "*Este*",
                "this (near the speaker)",
                "Masculine singular demonstrative for nearby things",
                "Este libro es mío.",
            ]
        ),
        TableRow(
            cells=[
                "*Ese*",
                "that (near the listener)",
                "Masculine singular demonstrative for things near the listener",
                "Ese libro es tuyo.",
            ]
        ),
        TableRow(
            cells=[
                "*Aquel*",
                "that (far from both)",
                "Masculine singular demonstrative for distant things",
                "Aquel libro es suyo.",
            ]
        ),
    ],
    adjective_table_layout="adj_other",
)

PROMPT_VARIABLES = {
    "native_language": "English",
    "target_language": "Spanish",
    "rule_name": "Noun Gender",
    "rule_description": "Masculine vs feminine",
}


class FakeAdjectiveLLM:
    """Classifier-first fake: returns a layout choice, then canned tables.

    Dispatches on the structured-output schema: AdjectiveTableLayoutClassification
    calls get the configured layout, TableData calls pop the queued tables.
    Records classifier vs table prompts separately, plus a combined list.
    """

    def __init__(self, layout: str, tables):
        self.layout = layout
        self.tables = list(tables)
        self.prompts: list[str] = []
        self.classifier_prompts: list[str] = []
        self.table_prompts: list[str] = []

    def with_structured_output(self, schema):
        def respond(prompt_value):
            prompt_str = prompt_value.to_string()
            self.prompts.append(prompt_str)
            if (
                getattr(schema, "__name__", "")
                == "AdjectiveTableLayoutClassification"
            ):
                self.classifier_prompts.append(prompt_str)
                from graphs.models import AdjectiveTableLayoutClassification

                return AdjectiveTableLayoutClassification(
                    adjective_table_layout=self.layout
                )
            self.table_prompts.append(prompt_str)
            return self.tables.pop(0)

        return RunnableLambda(respond)


class FakeRuleTextAdjectiveLLM(FakeAdjectiveLLM):
    """Classifier that derives OTHER from rule text, like the real prompt.

    Returns adj_other when the rule text mentions a special topic stem,
    otherwise the configured fallback layout. Proves OTHER is reached only
    via the classifier, with no language check.
    """

    SPECIAL_STEMS = (
        "demonstrativ",
        "possessiv",
        "comparativ",
        "superlativ",
        "apocop",
        "indefinit",
        "interrogativ",
        "ordinal",
    )

    def __init__(self, tables_by_layout: dict, fallback: str = "adj_number"):
        self.tables_by_layout = dict(tables_by_layout)
        self.fallback = fallback
        self.prompts: list[str] = []
        self.classifier_prompts: list[str] = []
        self.table_prompts: list[str] = []
        self.layouts: list[str] = []

    def with_structured_output(self, schema):
        def respond(prompt_value):
            prompt_str = prompt_value.to_string()
            self.prompts.append(prompt_str)
            if (
                getattr(schema, "__name__", "")
                == "AdjectiveTableLayoutClassification"
            ):
                self.classifier_prompts.append(prompt_str)
                from graphs.models import AdjectiveTableLayoutClassification

                rule_text = _rule_text(prompt_str).casefold()
                words = re.findall(r"[a-z]+", rule_text)
                layout = self.fallback
                if any(
                    word.startswith(stem)
                    for word in words
                    for stem in self.SPECIAL_STEMS
                ):
                    layout = "adj_other"
                self.layouts.append(layout)
                self.layout = layout
                self._table_calls = 0
                return AdjectiveTableLayoutClassification(
                    adjective_table_layout=layout
                )
            self.table_prompts.append(prompt_str)
            layout = self.layouts[-1] if self.layouts else self.fallback
            # Agreement fans out to number then gender generals in order.
            if layout in ("adj_agreement", "adj_agreement_number", "adj_agreement_gender"):
                step_layout = (
                    "adj_agreement_number"
                    if getattr(self, "_table_calls", 0) == 0
                    else "adj_agreement_gender"
                )
                self._table_calls = getattr(self, "_table_calls", 0) + 1
                tables = list(self.tables_by_layout[step_layout])
                table = tables.pop(0)
                self.tables_by_layout[step_layout] = tables
                return table
            tables = list(self.tables_by_layout[layout])
            table = tables.pop(0)
            self.tables_by_layout[layout] = tables
            return table

        return RunnableLambda(respond)


class FakeStructuredLLM:
    def __init__(self, result):
        self.result = result
        self.prompts: list[str] = []

    def with_structured_output(self, schema):
        def respond(prompt_value):
            self.prompts.append(prompt_value.to_string())
            return self.result

        return RunnableLambda(respond)


class FakeSequentialLLM:
    """Returns a canned TableData per call, in order.

    Used for the unified adjective flow, where the category node invokes one
    prompt for the number table and a second prompt for the gender table.
    """

    def __init__(self, results):
        self.results = list(results)
        self.prompts: list[str] = []

    def with_structured_output(self, schema):
        def respond(prompt_value):
            self.prompts.append(prompt_value.to_string())
            return self.results.pop(0)

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
