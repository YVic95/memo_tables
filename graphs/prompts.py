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
        Translate the following grammar rule name and description into {target_language} of the user.
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

        CRITICAL FORMATTING RULES:
        - Never use "#" alone as a separator between sections. Use blank lines instead.
        - Use "##" for the main heading: ## Grammar Rule: {rule_title}
        - Use "###" for section headings: ### Rule Statement:, ### Examples:, ### Common Mistakes:
        - Use "**" for emphasis on key terms.
        - Use "*" for translations and example phrases.
        - Use numbered lists (1. 2. ...) for examples.
        - Use "-" sub-lists within common mistakes.

        Follow this structure exactly:

        ## Grammar Rule: {rule_title}

        ### Rule Statement:
        [clear explanation of the rule]

        ### Examples:
        1. **[example in target language]** *([translation])* — [brief explanation]
        2. **[example]** *([translation])* — [explanation]
        3. **[example]** *([translation])* — [explanation]
        4. **[example]** *([translation])* — [explanation]
        5. **[example]** *([translation])* — [explanation]

        ### Common Mistakes:
        1. **[mistake name]**
           - Mistake: **[wrong example]**
           - Correction: **[correct example]** — [explanation]
        2. **[mistake name]**
           - Mistake: **[wrong example]**
           - Correction: **[correct example]** — [explanation]

        Include: clear rule statement, 3-5 examples with translations, and 1-2 common mistakes.
    """
)