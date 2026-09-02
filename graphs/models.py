import uuid
from pydantic import BaseModel, Field, field_validator

class Rule(BaseModel):
    title: str = Field(description="Short name of the grammar/language rule")
    explanation: str = Field(
        description=
        """
            Clear explanation of the rule, written in the user's native language.
            Keep it short and explain why the learner should know this rule.
        """
    )

class ProposedRules(BaseModel):
    rules: list[Rule] = Field(description="Exactly 5 proposed rules")

class CategoryChoice(BaseModel):
    word_category_id: uuid.UUID = Field(description="The id of the single best-fitting category")

class RuleTranslation(BaseModel):
    name: str = Field(description="Name translated to the target language of user")
    description: str = Field(description="Description translated to the target language of user")

class TableRow(BaseModel):
    cells: list[str] = Field(description="Cell values for this row, one per column")
    row_position: int | None = Field(
        default=None,
        description="Position of this row within its table, as provided by the caller",
    )

class TableData(BaseModel):
    title: str = Field(description="Heading for this table")
    headers: list[str] = Field(description="Column headers")
    rows: list[TableRow] = Field(description="Table rows")
    fragmented_table_id: int | None = Field(
        default=None,
        description="1-based id for fragmented sub-tables; None for a regular table",
    )

class FragmentationOutput(BaseModel):
    should_fragment: bool = Field(description="Whether the table can be split into sub-tables")
    fragmentation_rationale: str = Field(description="Explanation of the fragmentation decision")
    tables: list[TableData] = Field(description="Sub-tables if fragmented, empty otherwise")

class GenerateTableRequest(BaseModel):
    grammar_rule_id: uuid.UUID
    language_pair_id: uuid.UUID

class DeducedBaseWord(BaseModel):
    word: str = Field(description="Base/dictionary form of the word in the target language")
    native_translation: str = Field(description="Translation of the base word into the learner's native language")
    word_category_id: uuid.UUID = Field(description="The id of the best-fitting category for this base word, chosen from the provided list")
    surface_forms: list[str] = Field(description="The source surface forms (conjugated verb forms or example-sentence words) that map to this base word")

    @field_validator("surface_forms")
    @classmethod
    def dedupe_forms(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for form in v:
            key = form.lower()
            if key not in seen:
                seen.add(key)
                result.append(form)
        return result

class DeducedBaseWords(BaseModel):
    base_words: list[DeducedBaseWord] = Field(description="List of deduced base/dictionary word forms with their native-language translations")

class TranslationPair(BaseModel):
    text: str = Field(description="An exact input item from the items list")
    translation: str = Field(description="Its translation into the learner's native language")

class Translations(BaseModel):
    translations: list[TranslationPair] = Field(description="One entry per input item")

class SaveTablesRequest(BaseModel):
    language_pair_id: uuid.UUID
    session_id: uuid.UUID
    grammar_rule_id: uuid.UUID
    tables: list[TableData]