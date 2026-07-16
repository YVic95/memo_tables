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
    name: str = Field(description="Translated name")
    description: str = Field(description="Translated description")