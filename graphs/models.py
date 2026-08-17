from pydantic import BaseModel, Field

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
    word_category_id: str = Field(description="The id of the single best-fitting category")

class RuleTranslation(BaseModel):
    name: str = Field(description="Name translated to the target language of user")
    description: str = Field(description="Description translated to the target language of user")

class TableRow(BaseModel):
    cells: list[str] = Field(description="Cell values for this row, one per column")

class TableData(BaseModel):
    title: str = Field(description="Heading for this table")
    headers: list[str] = Field(description="Column headers")
    rows: list[TableRow] = Field(description="Table rows")

class FragmentationOutput(BaseModel):
    should_fragment: bool = Field(description="Whether the table can be split into sub-tables")
    fragmentation_rationale: str = Field(description="Explanation of the fragmentation decision")
    tables: list[TableData] = Field(description="Sub-tables if fragmented, empty otherwise")

class GenerateTableRequest(BaseModel):
    grammar_rule_id: str
    language_pair_id: str

class SaveTablesRequest(BaseModel):
    language_pair_id: str
    session_id: str
    grammar_rule_id: str
    tables: list[TableData]