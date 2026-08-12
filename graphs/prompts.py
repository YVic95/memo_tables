from langchain_core.prompts import PromptTemplate

propose_rules_prompt = PromptTemplate.from_template(
    """
        You are a language-learning content expert.

        Suggest exactly 5 fundamental grammar or usage rules a native
        {native_language} speaker should learn first when studying
        {target_language}.

        Keep explanations concise and beginner-friendly.

        Rules should be written in the {native_language} of the user.

        Each rule must cover exactly one grammatical concept — do not
        combine multiple items from the list below into a single rule:
        - Tense formation: cover only one tense per rule
          (e.g. do not combine present and past in one rule).
        - Gender agreement: cover only one gender pairing or category per rule
          (e.g. do not combine masculine/feminine noun rules with
          adjective agreement in one rule).
        - Plural formation: cover only one pluralization pattern per rule
          (e.g. do not combine regular and irregular plural rules together).
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

generate_table_prompt = PromptTemplate.from_template(
    """
    You are a language-learning content expert. Create a grammar or conjugation
    table that teaches the rule below to a learner whose native language is
    {native_language} and who is learning {target_language}.

    Rule name: {rule_name}
    Rule description: {rule_description}

    LANGUAGE RULES
    - Table title: written in {target_language}, briefly summarizing the rule.
    - Column headers: written in {target_language} (e.g. "Person", "Singular", "Plural").
    - Explanation text inside cells: written in {native_language}, so the learner
      understands *why* the form is used.
    - Word forms and examples inside cells: written in {target_language}, 
    - Select one representative lexical item (verb, noun, adjective, etc.) for
      the entire table.
    - Every example in the table must use this same lexical item.
    - Only change its grammatical form as required by the rule.
    - Do not introduce additional lexical items to demonstrate different rows.

    COLUMN STRUCTURE — output EXACTLY these three columns, in this order, and no others:
    1. Form — MUST include both the subject/case marker (if any, e.g. pronoun) 
        AND the target-language word form together in a single cell 
        (e.g. "je parlerai", not split across two columns).
        This is the primary key of the row: if a row would have no meaningful
        content at all, omit it entirely rather than including it with empty cells.
        However, if the rule includes a case where no word/form is used (e.g. the
        "zero article" before uncountable or plural nouns), keep that row and
        label the cell descriptively (e.g. "(no article)") instead of
        leaving it blank — the row itself is meaningful even though the form is absent.
    2. Explanation — a short explanation, in {target_language}, of when/why this
       form is used.
    3. Example — a short {target_language} sentence or phrase illustrating the form.
      The entire table must use the SAME lexical item (e.g. the same verb, noun,
      or adjective). Only its grammatical form may change according to the rule.
      Do not switch to different words between rows.
    Do not add, omit, reorder, or split any of these three columns under any circumstances.

    CONTENT RULES
    - Cover all grammatically meaningful persons/forms/cases relevant to this rule
      (e.g. all persons for a conjugation rule, all cases for a declension rule).
    - Do not include separate "Common mistake" or "Correction" columns or content.
    - Do not create more than one "Example" column. If a row has multiple example
      instances, put them all together inside the single Example cell (e.g. as a
      short list), rather than splitting them across columns.
    - Do not repeat or re-explain an aspect of the rule that was already covered
      in an earlier row — each row should add new information.
    - If a form does not apply to a given row, use an empty string ("") for that
      cell rather than "N/A" or similar filler.
    - If an entire column would end up empty across all rows, omit that column
      entirely rather than including it with blank cells.

    Return only the table (title, headers, rows) — no additional commentary
    before or after it.
    """
)

fragmentation_prompt = PromptTemplate.from_template(
    """
        Analyse the following grammar table and decide if it can be split into smaller,
        pedagogically useful sub-tables.

        Table: {general_table_json}

        Rules:
        - Split only if the table has at least 2 distinct logical groups (e.g. singular/plural,
          masculine/feminine, present/past, etc.)
        - Each sub-table must be self-contained and have at least 2 rows.
        - If the table is already small or cannot be cleanly divided, set should_fragment to false.
        - Provide a brief rationale for your decision.

        Output should_fragment, a short rationale, and the list of sub-tables (empty if not fragmenting).
    """
)
### Common Mistakes:
        # 1. **[mistake name]**
        #    - Mistake: **[wrong example]**
        #    - Correction: **[correct example]** — [explanation]
        # 2. **[mistake name]**
        #    - Mistake: **[wrong example]**
        #    - Correction: **[correct example]** — [explanation]

        # Include: clear rule statement, 3-5 examples with translations, and 1-2 common mistakes.
        ### Common Mistakes: -> put it in the section heading when needed
        # - Use "-" sub-lists within common mistakes. -> put it in the CRITICAL FORMATTING RULES when needed

rule_content_prompt = PromptTemplate.from_template(
    """
        Write the full learning content for this grammar rule, in {native_language},
        for a speaker learning {target_language}.

        Name: {rule_title}
        Short explanation: {rule_explanation}

        CRITICAL FORMATTING RULES:
        - Never use "#" alone as a separator between sections. Use blank lines instead.
        - Use "##" for the main heading: ## Grammar Rule: {rule_title}
        - Use "###" for section headings: ### Rule Statement:, ### Examples:
        - Use "**" for emphasis on key terms.
        - Use "*" for translations and example phrases.
        - Use numbered lists (1. 2. ...) for examples.

        Follow this structure exactly:

        ## Grammar Rule: {rule_title}

        ### Rule Statement:
        [clear explanation of the rule]

        ### Examples:
        Select ONE representative lexical item (verb, noun, adjective, etc.) for
        all examples.
        1. **[example in target language]** *([translation])* — [brief explanation]
        2. **[example]** *([translation])* — [explanation]
        3. **[example]** *([translation])* — [explanation]
        4. **[example]** *([translation])* — [explanation]
        5. **[example]** *([translation])* — [explanation]

    """
)

edit_table_prompt = PromptTemplate.from_template(
    """
    You are a language-learning content expert. You are editing an existing
    grammar or conjugation table based on the learner's instructions.

    Learner's native language: {native_language}
    Language being studied: {target_language}

    User instructions:
    {instructions}

    Current table:
    {table_json}

    Previous edits made earlier in this chat (most recent last):
    {previous_edits}

    EDITING RULES
    - If the user's instructions refer to applying the same edits as a previous
      edit in this chat (e.g. "same edits", "same as before", "like the previous
      table"), reproduce those exact changes on the current table, adapting cell
      values as needed to fit this table's content. Otherwise, apply ONLY the
      changes explicitly requested in the current instructions.
    - Treat every column NOT mentioned in the instructions as LOCKED: copy its
      cell values from the current table byte-for-byte, even if they now seem
      redundant, inconsistent, or oddly paired with an edited column. Do not
      infer that an edit to one column requires edits to another.
    - If the user's instructions are ambiguous about scope (e.g. they name a
      single column but the phrasing could also be read as applying to the whole
      table), assume the NARROWEST interpretation: apply the change to only the
      named column.
    - Never replace a cell's content with an empty string ("") unless the user's
      instructions explicitly ask to remove or clear that specific cell/column.
    - Before returning, verify: every row/column not named in the instructions
      must be identical to the current table.

    Return only the edited table (title, headers, rows) — no additional commentary
    before or after it.
    """
)