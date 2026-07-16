from langchain_core.prompts import PromptTemplate

propose_rules_prompt = PromptTemplate.from_template(
    """
        You are a language-learning content expert.

        Suggest exactly 5 fundamental grammar or usage rules a native
        {native_language} speaker should learn first when studying
        {target_language}.

        Keep explanations concise and beginner-friendly.

        Rules should be written in the {native_language} of the user.
    """
)

attach_grammar_category_to_rule_prompt = PromptTemplate.from_template(
    """
        You are classifying a grammar rule into a grammatical category.
        Rule title: {rule_title}
        Rule explanation: {rule_explanation}

        Choose exactly one category id from this list that best fits:
        {categories}
    """
)

translate_prompt = PromptTemplate.from_template(
    """
        Translate the following grammar rule name and description into {native_language}.
        Name: {rule_title}
        Description: {rule_explanation}
    """
)

rule_content_prompt = PromptTemplate.from_template(
    """
        Write the full learning content for this grammar rule, in {native_language},
        for a speaker learning {target_language}.
        Name: {rule_title}
        Short explanation: {rule_explanation}

        Include: clear rule statement, 3-5 examples with translations, and 1-2 common mistakes.
    """
)