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
    - Word forms and examples inside cells: written in {target_language}.
    - Select one representative lexical item (verb, noun, adjective, etc.) for
      the entire table. Do not introduce additional lexical items anywhere in
      the table.

    CARRIER SENTENCE (for the Example column)
    - Before filling in rows, design ONE short carrier sentence/phrase template
      in {target_language} that can host every form in the table (e.g. a short
      frame like "___ tous les jours" for a verb-conjugation rule, or an
      equivalent minimal frame for a case/declension rule).
    - Use this exact same carrier sentence for every row's Example cell, changing
      ONLY the target word/form itself (and, if grammatically required, the
      minimum surrounding agreement — e.g. an article or ending that must
      agree with a changing case). Do not alter word order, vocabulary, or
      any other part of the carrier sentence between rows.
    - If a row's form cannot be inserted into the carrier sentence at all
      (e.g. a "zero form" row), keep the carrier sentence but mark the slot
      descriptively (e.g. "(no article) ___ tous les jours").
    - Choose the carrier sentence so that it remains natural and grammatical
      across all rows; if no single sentence can host every row naturally,
      choose the shortest phrase/frame that can.

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
    3. Example — the carrier sentence defined above, with this row's form
       inserted into it. Exactly one instance per row; do not list multiple
       example sentences in a single cell.
    Do not add, omit, reorder, or split any of these three columns under any circumstances.

    CONTENT RULES
    - Cover all grammatically meaningful persons/forms/cases relevant to this rule
      (e.g. all persons for a conjugation rule, all cases for a declension rule).
    - Do not include separate "Common mistake" or "Correction" columns or content.
    - Do not repeat or re-explain an aspect of the rule that was already covered
      in an earlier row — each row should add new information.
    - If a form does not apply to a given row, use an empty string ("") for that
      cell rather than "N/A" or similar filler.
    - If an entire column would end up empty across all rows, omit that column
      entirely rather than including it with blank cells.
    - If language use diacritics - use them in a proper way.

    Return only the table (title, headers, rows) — no additional commentary
    before or after it.
    """
)

generate_verb_table_prompt = PromptTemplate.from_template(
    """
    You are a language-learning content expert. Create a verb conjugation
    table that teaches the rule below to a learner whose native language is
    {native_language} and who is learning {target_language}.

    Rule name: {rule_name}
    Rule description: {rule_description}

    COLUMN STRUCTURE — output EXACTLY these five columns, in this order, and no others:
    1. Pronoun — the subject pronoun in {target_language} (e.g. "ich", "du",
       "er/sie/es" for German), must start from uppercase letter. 
       If the target language is pro-drop (pronouns can
       be omitted), still include the pronoun column but mark rows where the
       pronoun is optional with a note like "ich (optional)".
    2. Verb — the conjugated verb form in {target_language}.
       Also must start from uppercase letter.
    3. Example — a short sentence in {target_language} using that conjugation.
    4. Explanation — in {native_language}, explaining when/why this form is used.

    LANGUAGE RULES
    - Table title: written in {target_language}, summarizing the conjugation rule.
    - Column headers: written in {target_language}.
    - Explanation text inside cells: written in {native_language}, so the learner
      understands *why* the form is used.
    - All other cells (Person, Pronoun, Verb, Example): written in
      {target_language}.
    - Select ONE representative verb for the entire table. Every row must use
      this same verb. Only change its conjugation form per row.
    - Do not introduce additional lexical items to demonstrate different rows.

    CONTENT RULES
    - Cover all grammatically meaningful persons relevant to this rule
      (e.g. all persons for a regular present-tense conjugation, or a subset
      if the rule only covers certain forms).
    - If a form does not apply to a given row, use "" rather than "N/A" or
      similar filler.
    - Do not include separate "Common mistake" or "Correction" columns or content.
    - Do not repeat or re-explain an aspect of the rule that was already covered
      in an earlier row — each row should add new information.

    Return only the table (title, headers, rows) — no additional commentary
    before or after it.
    """
)

fragmentation_prompt = PromptTemplate.from_template(
    """
        Analyse the following grammar table and decide if it can be split into smaller,
        pedagogically useful sub-tables. The table may be in any language and cover any
        grammatical topic (conjugation, declension, word order, particles, etc.).

        Table: {general_table_json}

        Step 1 — Identify grouping axes:
        Examine every column, especially any column naming grammatical categories —
        person, number, gender, case, tense, aspect, mood, formality/register, animacy,
        or similar — even if the column header is generic (e.g. "Form", "Category",
        or a native-language label like "Osoba", "Persona", "人称"). For each such
        column, determine whether its values fall into 2 or more natural groups
        (e.g. singular forms vs plural forms, masculine vs feminine vs neuter,
        formal vs informal, present vs past), with each group containing at least
        2 rows.

        Step 2 — Decide:
        - If ANY axis from Step 1 produces 2+ groups with at least 2 rows each,
          set should_fragment to true and split along that axis — EVEN IF the table
          looks short overall. Row count alone is never a reason to skip splitting;
          what matters is whether a clean grouping exists.
        - If multiple axes qualify, choose the one most useful for a learner
          (typically the axis a learner would need to master as a distinct rule,
          e.g. splitting by number before splitting by formality).
        - Only set should_fragment to false if no axis produces 2+ valid groups —
          for example, the table already represents one homogeneous grammatical
          category, or any split would leave a group with fewer than 2 rows.
        - Each sub-table must be self-contained: retain enough context (labels,
          headers, brief explanation) that it makes sense read on its own, without
          referring back to the original table.

        Do not rely on absolute table size as a proxy for "already small enough" —
        judge only by whether a coherent grouping axis with 2+ qualifying groups
        exists.

        Output should_fragment, a short rationale naming the grouping axis used
        (or explaining why none qualified), and the list of sub-tables (empty if
        not fragmenting).
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
        for a speaker learning {target_language}. Cover all gramatical forms for concrete rule.

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
        all examples. Use ONLY ONE word for all examples.

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

deduce_base_word_prompt = PromptTemplate.from_template(
    """
        You are a linguistics expert. Given a list of surface word forms in
        {target_language} — the conjugated verb forms from a verb table, plus
        the words tokenized out of its example sentences — deduce the base
        (dictionary) form of each content word and assign it a word category.

        The main verb of the table must always be assigned the word category:
        {rule_word_category}

        Available word categories — choose exactly one id for every base word:
        {available_categories}

        Surface forms:
        {surface_forms}

        Rules:
        - Group every surface form under its base/dictionary form. If several
          surface forms share a base form, list that base form only once and put
          each surface form in its surface_forms list.
        - Only include CONTENT words (nouns, verbs, adjectives, adverbs). Skip
          function words: pronouns, articles, prepositions, conjunctions,
          particles, and any other non-content items.
        - Assign the main verb's base form the category {rule_word_category}.
        - For every other base word, choose the single best-fitting category id
          from the available list.

        Return only the base words with their category ids and surface forms —
        no additional commentary.
    """
)

translate_words_prompt = PromptTemplate.from_template(
    """
    You are a translation assistant for a language-learning app.
    Translate each of the following items from {target_language} into
    {native_language}.

    Items:
    {items}

    Return a list with exactly one entry per input item. For each entry, set
    `text` to the item exactly as given (same spelling and case) and
    `translation` to its {native_language} translation. Keep translations
    short and natural. If an item is identical, return it unchanged.
    """
)
