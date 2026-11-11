from langchain_core.prompts import PromptTemplate

from graphs.models import MAX_SIMILAR_RULES_SHOWN

propose_missing_rules_prompt = PromptTemplate.from_template(
    """
        You are a language-learning content expert.

        Below is the catalog of grammar rules that a native {native_language}
        speaker should be taught when studying {target_language}. These are the
        ONLY rules available — never invent a rule that is not in the catalog.

        Choose up to ten rules from the catalog to teach next. The catalog is
        already ordered by difficulty (CEFR level, then position), so prefer the
        most fundamental missing rules first.

        For every rule you choose, return its canonical_rule_id exactly as shown
        in the catalog, phrase the title in {native_language}, and keep the
        explanation concise and beginner-friendly, written in {native_language}.

        Catalog:
        {candidates}
    """
)

translate_prompt = PromptTemplate.from_template(
    """
        Translate the following grammar rule name and description into {target_language} of the user.
        Name: {rule_title}
        Description: {rule_explanation}
    """
)

duplicate_check_prompt = PromptTemplate.from_template(
    """
        You are checking whether a proposed grammar rule duplicates a rule that
        is already taught.

        Below is the proposed rule's title and explanation, followed by existing
        rules that are already persisted. Each existing rule is listed with its
        id, its stored name, and its description.

        Compare the proposal against each existing rule on BOTH its name and its
        description. A rule whose name has been reworded is still a duplicate if
        its description teaches the same thing, and the other way round.

        Decide whether any existing rule teaches the SAME grammar rule as the
        proposed one — the same underlying grammar concept, not merely a related
        topic. The wording does not have to match exactly; an overlap on either
        the name or the description is enough to make a candidate a match. A rule
        may match alongside others that also match, so name every candidate that
        is a genuine duplicate, ordered best match first, and return similar=true
        with their ids exactly as shown.

        Name at most {max_matches}. Return fewer when fewer are genuine duplicates,
        and return none when none are: a short list is the right answer whenever you
        are unsure of a candidate, so do not pad the list with related rules to
        fill it. A rule on an adjacent topic is not a duplicate just because it
        overlaps in vocabulary.

        Otherwise return similar=false with no ids.

        Proposed title: {rule_title}
        Proposed explanation: {rule_explanation}

        Existing rules:
        {candidates}
    """,
    partial_variables={"max_matches": MAX_SIMILAR_RULES_SHOWN},
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

generate_noun_table_prompt = PromptTemplate.from_template(
    """
    You are a language-learning content expert. Create a noun table that
    teaches the rule below to a learner whose native language is
    {native_language} and who is learning {target_language}.

    Rule name: {rule_name}
    Rule description: {rule_description}

    CHOOSE THE LAYOUT
    Decide which of the two layouts fits the rule, then set `noun_table_layout` to
    the matching value and use that layout's eight columns.
    - NUMBER layout ("noun_number") — for a rule about singular/plural, number,
      or how plurals are formed.
    - GENDER layout ("noun_gender") — for a rule about grammatical gender
      (masculine/feminine) that does not teach plural formation.
    - If the rule covers BOTH gender and number, use the NUMBER layout and set
      noun_table_layout to "noun_number"; mention gender in the explanations.

    The column names below describe each column's role. Output the headers in
    {target_language}, keeping this exact order and meaning.

    NUMBER LAYOUT — noun_table_layout "noun_number"
    1. Singular
    2. Translation
    3. Explanation
    4. Example
    5. Plural
    6. Translation
    7. Explanation
    8. Example

    GENDER LAYOUT — noun_table_layout "noun_gender"
    1. Masculine
    2. Translation
    3. Explanation
    4. Example
    5. Feminine
    6. Translation
    7. Explanation
    8. Example

    ROW STRUCTURE — one row = one pair
    - Number layout: the same noun in singular (columns 1-4) and plural
      (columns 5-8).
    - Gender layout: a masculine noun (columns 1-4) paired with a feminine noun
      (columns 5-8) that shows the same pattern or the same exception
      (e.g. "el libro" / "la mesa", "el problema" / "la mano").

    CONTENT RULES
    - Table title: written in {target_language}, briefly summarizing the rule.
    - Column headers: written in {target_language}, in the chosen layout's order.
    - The form columns (Singular/Plural or Masculine/Feminine): the noun in
      {target_language}, with its article where the language uses one.
    - Translation cells: written in {native_language} and include the article,
      e.g. "the table".
    - Explanation cells: written in {native_language}, as short grammar notes.
      Left side: the gender cue or the singular article. Right side: the plural
      formation or the feminine cue.
    - Example cells: exactly one short sentence in {target_language} using that
      side's noun form. Do not include a native-language translation in the cell.
    - Pair count:
      - Single-pattern rule: generate 2-3 pairs.
      - Multi-pattern rule: generate 4-6 pairs.
    - Every row must have exactly eight cells.
    - Do not add, omit, reorder, or split any of the eight columns.
    - Do not include separate "Common mistake" or "Correction" columns or content.
    - If the language uses diacritics, use them properly.

    Return only the table (title, headers, rows, noun_table_layout) — no additional
    commentary before or after it.
    """
)

generate_adjective_number_table_prompt = PromptTemplate.from_template(
    """
    You are a language-learning content expert. Create an adjective number
    table that teaches the rule below to a learner whose native language is
    {native_language} and who is learning {target_language}.

    Rule name: {rule_name}
    Rule description: {rule_description}

    This is the entry table of the adjective flow: depending on the rule it
    produces either the NUMBER table of a unified number+gender pair (a
    separate GENDER table follows), a single AGREEMENT table, or a single
    OTHER table.

    CHOOSE THE TABLE
    Decide which of the three tables fits the rule, then set
    `adjective_table_layout` to the matching value and use that layout's
    columns. Check the OTHER table first: special adjective topics always win,
    no matter what else the rule mentions.
    - OTHER table ("adj_other") — for a closed set of forms or a special
      adjective topic (demonstrative, possessive, comparative, superlative,
      apocope, indefinite, interrogative, ordinal, ...). The table lists each
      form directly: adjective, translation,
      explanation, example. ALWAYS use this table for such rules, even if
      the rule also mentions number or gender.
    - NUMBER table ("adj_number_gender") — for a rule about general
      inflection of regular adjectives (singular/plural or gender endings)
      that does not teach noun-adjective agreement and is not about a
      special topic above. The gender companion table is generated
      separately afterwards.
    - AGREEMENT table ("adj_agreement") — for a rule about nouns and
      regular adjectives agreeing in gender and number.
      If the rule covers BOTH gender and number, use the AGREEMENT table.

    The column names below describe each column's role. Output the headers in
    {target_language}, keeping this exact order and meaning.

    NUMBER LAYOUT — adjective_table_layout "adj_number_gender"
    1. Singular
    2. Translation
    3. Explanation
    4. Example
    5. Plural
    6. Translation
    7. Explanation
    8. Example

    AGREEMENT LAYOUT — adjective_table_layout "adj_agreement"
    1. Masculine
    2. Translation
    3. Explanation
    4. Example
    5. Feminine
    6. Translation
    7. Explanation
    8. Example

    OTHER LAYOUT — adjective_table_layout "adj_other"
    1. Adjective
    2. Translation
    3. Explanation
    4. Example

    ROW STRUCTURE
    - Number and agreement layouts: one row = one pair (see below).
    - Other layout: one row = one form (columns 1-4): the adjective, its
      translation, a usage note, and an example sentence. Cover every form in
      a finite set; for productive topics, use representative forms that teach
      the pattern rather than listing every adjective in the language.
    - Number layout: the same adjective in singular (columns 1-4) and plural
      (columns 5-8), each inside a carrier noun+adjective phrase with its
      definite article (e.g. "el libro rojo / los libros rojos").
      Use a DIFFERENT adjective in each row.
    - Agreement layout: one adjective in its masculine and feminine forms
      (columns 1-4 and 5-8), each inside a full noun+adjective agreement
      phrase with its definite article.
      For example: "el libro rojo / la mesa roja".
      Use a DIFFERENT adjective in each row.

    CONTENT RULES
    - Table title: written in {target_language}, briefly summarizing the rule.
      Use a distinct title from the companion gender table when the number
      layout is chosen.
    - Column headers: written in {target_language}, in the chosen layout's order.
    - The form columns (Singular/Plural or Masculine/Feminine, i.e. the number
      and agreement layouts): the carrier
      noun+adjective phrase in {target_language}, with the definite article.
      Never list a bare adjective. Cells hold plain text with no markers.
    - Other layout: the Adjective column holds the bare form in
      {target_language} with an uppercase first letter (e.g. "Este"); the
      Translation column holds the {native_language} translation; the
      Explanation column holds a short usage note in {native_language}; the
      Example column holds exactly one short sentence in {target_language}
      using the form, with no native-language translation in the cell.
    - Translation cells: written in {native_language} and include the article
      where one applies, e.g. "the red book".
    - Explanation cells: written in {native_language}, as short grammar notes.
      Number layout, left side: the gender cue or the singular article. Right
      side: how the plural is formed (noun and adjective). Agreement layout,
      left side: the masculine agreement cue. Right side: the feminine
      agreement cue.
    - Example cells: exactly one short sentence in {target_language} using that
      side's phrase. Do not include a native-language translation in the cell.
    - Pair count:
      - Single-pattern rule: generate 2-3 pairs.
      - Multi-pattern rule: generate 4-6 pairs.
      - Other layout: there is no row cap. Include the full finite inventory or
        enough representative forms for a productive topic; the table is never
        split.
    - Number and agreement layouts: every row must have exactly eight cells.
      Other layout: every row must have exactly four cells.
    - Do not add, omit, reorder, or split any columns of the chosen layout.
    - Do not include separate "Common mistake" or "Correction" columns or content.
    - If the language uses diacritics, use them properly.

    Return only the table (title, headers, rows, adjective_table_layout) — no
    additional commentary before or after it.
    """
)

generate_adjective_gender_table_prompt = PromptTemplate.from_template(
    """
    You are a language-learning content expert. Create an adjective gender
    table that teaches the rule below to a learner whose native language is
    {native_language} and who is learning {target_language}.

    Rule name: {rule_name}
    Rule description: {rule_description}

    This is the GENDER table of a unified number+gender pair: the NUMBER table
    (singular/plural) already exists for the same rule. Set
    `adjective_table_layout` to "adj_number_gender" and use these eight
    columns. Use the same KIND of adjectives as the number table (regular,
    possessive, demonstrative, ...): only the dimension changes. The avoid
    list below still applies, so choose fresh items of that same kind.

    The column names below describe each column's role. Output the headers in
    {target_language}, keeping this exact order and meaning.

    GENDER LAYOUT — adjective_table_layout "adj_number_gender"
    1. Masculine
    2. Translation
    3. Explanation
    4. Example
    5. Feminine
    6. Translation
    7. Explanation
    8. Example

    ROW STRUCTURE — one row = one pair
    A masculine carrier phrase (columns 1-4) paired with a feminine carrier
    phrase (columns 5-8) showing the same adjective pattern. For example:
    "el libro rojo / la mesa roja". Use a DIFFERENT adjective in each row.
    Do not reuse these adjectives or carrier nouns — they already appear in
    the number table: {avoid_phrases}. (If that list is empty, ignore this rule.)

    CONTENT RULES
    - Table title: written in {target_language}, briefly summarizing the
      gender aspect of the rule. Use a distinct title from the companion
      number table.
    - Column headers: written in {target_language}, in the layout order above.
    - The form columns (Masculine/Feminine): the carrier noun+adjective phrase
      in {target_language}, with the definite article. Never list a bare adjective.
      Cells hold plain text with no markers.
    - Translation cells: written in {native_language} and include the article,
      e.g. "the red book".
    - Explanation cells: written in {native_language}, as short grammar notes.
      Left side: the masculine cue. Right side: the feminine cue.
    - Example cells: exactly one short sentence in {target_language} using that
      side's phrase. Do not include a native-language translation in the cell.
    - Pair count:
      - Single-pattern rule: generate 2-3 pairs.
      - Multi-pattern rule: generate 4-6 pairs.
    - Every row must have exactly eight cells.
    - Do not add, omit, reorder, or split any of the eight columns.
    - Do not include separate "Common mistake" or "Correction" columns or content.
    - If the language uses diacritics, use them properly.

    Return only the table (title, headers, rows, adjective_table_layout) — no
    additional commentary before or after it.
    """
)

generate_adjective_other_table_prompt = PromptTemplate.from_template(
    """
    You are a language-learning content expert. Create a table for this special
    adjective topic for a learner whose native language is
    {native_language} and who is learning {target_language}.

    Rule name: {rule_name}
    Rule description: {rule_description}

    This is a special-topic rule in the Spanish adjective catalog (such as
    demonstrative, possessive, comparative, superlative, apocope, indefinite,
    interrogative, or ordinal adjectives). Do not choose another layout.
    Set `adjective_table_layout` to "adj_other" and return exactly four columns:
    Adjective, Translation, Explanation, Example. Write the title and headers in
    {target_language}; write translations and usage notes in {native_language}.
    The Adjective column contains each distinct, capitalized target-language
    form. The Example column contains one short target-language sentence using
    that form. Include every form when the rule has a finite inventory; for
    productive topics, choose representative forms that illustrate the pattern.
    There is no arbitrary row cap.
    Do not use carrier noun phrases, add other columns, or split the table.
    Every row must have exactly four cells.

    Return only the table (title, headers, rows, adjective_table_layout), with
    adjective_table_layout "adj_other".
    """
)

fragmentation_prompt = PromptTemplate.from_template(
    """
        Analyse the following grammar table and decide if it can be split into smaller,
        pedagogically useful sub-tables. The table may be in any language and cover any
        grammatical topic (conjugation, declension, word order, particles, etc.).

        Table: {general_table_json}

        Step 1 — Enumerate ALL grouping axes:
        Examine EVERY column, especially any column naming grammatical categories —
        person, number, gender, case, tense, aspect, mood, formality/register, animacy,
        or similar — even if the column header is generic (e.g. "Form", "Category",
        or a native-language label like "Osoba", "Persona", "人称"). For EACH such
        column, independently check whether its values fall into 2 or more natural
        groups (e.g. singular vs plural, masculine vs feminine vs neuter, formal vs
        informal, present vs past), with each group containing at least 2 rows.

        Do not stop at the first axis that qualifies. List every column you examined,
        state whether it qualifies as a splitting axis, and if so, list its groups and
        row counts. A verb conjugation table, for example, will often have BOTH a
        person axis (1st/2nd/3rd) and a number axis (singular/plural) that qualify
        simultaneously — you must surface both, not just the first one you notice.

        Step 2 — Choose the axis (or combination):
        - If NO axis produces 2+ groups with at least 2 rows each, set should_fragment
          to false. Row count of the table is never itself a reason to skip splitting.
        - If exactly ONE axis qualifies, use it.
        - If MULTIPLE axes qualify, prefer the axis that reflects the more fundamental
          morphological/grammatical distinction for a learner, using this priority
          order as a default (override it only if the table clearly argues otherwise):
              tense/aspect > mood > number > person > gender > formality/register > other
          Rationale: distinctions like number often correspond to different stems or
          endings across the whole paradigm, while person is typically a finer-grained
          pattern *within* a number group — so splitting by number first is usually
          more useful before further splitting by person.
        - If two qualifying axes are both pedagogically important and the table is
          large enough to support it, you may nest them (e.g. split by number first,
          then by person within each number sub-table) rather than force a single flat
          split. Only do this if each resulting sub-table still has at least 2 rows.
        - Each sub-table must be self-contained: retain enough context (labels,
          headers, brief explanation) that it makes sense read on its own, without
          referring back to the original table.

        Output:
        - axes_considered: list of every candidate axis examined, whether it qualified,
          and its groups/row counts.
        - should_fragment
        - rationale: name the grouping axis (or nested axes) used, and explicitly state
          why it was chosen over any other qualifying axis found in Step 1.
        - sub_tables: list of sub-tables (empty if not fragmenting).
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

general_rule_content_prompt = PromptTemplate.from_template(
    """
        Write the full learning content for this grammar rule, in {native_language},
        for a speaker learning {target_language}. Cover all grammatical forms for concrete rule.

        Name: {rule_title}
        Short explanation: {rule_explanation}

        CRITICAL FORMATTING RULES:
        - Never use "#" alone as a separator between sections. Use blank lines instead.
        - Use "##" for the main heading: ## Grammar Rule: {rule_title}
        - Use "###" for section headings: ### Rule Statement:, ### Examples:
        - Use "**" for emphasis on key terms.
        - Use "*" for translations and example phrases.
        - Use numbered lists (1. 2. ...) for examples.
        - Each numbered example MUST be a single line. Do not put the forms or
          the translation on separate lines: a multi-line item breaks the numbering.

        Follow this structure exactly:

        ## Grammar Rule: {rule_title}

        ### Rule Statement:
        [clear explanation of the rule]

        ### Examples:
        Select ONE representative lexical item for all examples.
        Use ONLY ONE word for all examples.

    """
)

verb_rule_content_prompt = PromptTemplate.from_template(
    """
        Write the full learning content for this verb grammar rule, in {native_language},
        for a speaker learning {target_language}. Cover all grammatical forms for concrete rule.

        Name: {rule_title}
        Short explanation: {rule_explanation}

        CRITICAL FORMATTING RULES:
        - Never use "#" alone as a separator between sections. Use blank lines instead.
        - Use "##" for the main heading: ## Grammar Rule: {rule_title}
        - Use "###" for section headings: ### Rule Statement:, ### Examples:
        - Use "**" for emphasis on key terms.
        - Use "*" for translations and example phrases.
        - Use numbered lists (1. 2. ...) for examples.
        - Each numbered example MUST be a single line. Do not put the verb forms or
          the translation on separate lines: a multi-line item breaks the numbering.

        Follow this structure exactly:

        ## Grammar Rule: {rule_title}

        ### Rule Statement:
        [clear explanation of the rule]

        ### Examples:
        Select ONE representative verb for all examples. Use ONLY ONE verb
        for all examples, and do not write a sentence saying that one verb
        will be used for all of them.

        For each example, write one numbered line that shows the conjugated
        form(s) the rule is about and a short translation in {native_language}.
        Keep the whole example on that line. Cover every person the rule
        applies to, e.g.:
        1. **hablo / hablas** — I speak / you speak

    """
)

noun_rule_content_prompt = PromptTemplate.from_template(
    """
        Write the full learning content for this noun grammar rule, in
        {native_language}, for a speaker learning {target_language}. Cover all
        grammatical forms for the concrete rule.

        Name: {rule_title}
        Short explanation: {rule_explanation}

        CRITICAL FORMATTING RULES:
        - Never use "#" alone as a separator between sections. Use blank lines instead.
        - Use "##" for the main heading: ## Grammar Rule: {rule_title}
        - Use "###" for section headings: ### Rule Statement:, ### Examples:
        - Use "**" for emphasis on key terms.
        - Use "*" for translations and example phrases.
        - Use numbered lists (1. 2. ...) for examples.
        - Each numbered example MUST be a single line. Do not put the noun forms or
          the translation on separate lines: a multi-line item breaks the numbering.
        - Every noun MUST appear with its definite article in {target_language}
          (for example el/la/los/las in Spanish). Never list a bare noun.

        Follow this structure exactly:

        ## Grammar Rule: {rule_title}

        ### Rule Statement:
        [clear explanation of the rule]

        ### Examples:
        Use 4-5 examples. Use a DIFFERENT noun (or noun pair) in each example.
        Do not use only one noun for all examples, and do not write a sentence
        saying that one noun will be used for all of them.

        For each example, write one numbered line that shows the form(s) the rule
        is about and a short translation in {native_language}. Keep the whole
        example on that line. Always include the definite article with each noun.

        - For a singular/plural rule, show both forms, e.g.:
          1. **el libro / los libros** — the book / the books
          2. **el dólar / los dólares** — the dollar / the dollars
        - For a gender rule, pair a masculine and a feminine noun, e.g.:
          1. **el libro / la mesa** — the book (masculine) / the table (feminine)

        Choose nouns that illustrate the rule clearly, including important spelling,
        article, or gender patterns.
    """
)

adjective_rule_content_prompt = PromptTemplate.from_template(
    """
        Write the full learning content for this adjective grammar rule, in
        {native_language}, for a speaker learning {target_language}. Cover all
        grammatical forms for the concrete rule.

        Name: {rule_title}
        Short explanation: {rule_explanation}

        CRITICAL FORMATTING RULES:
        - Never use "#" alone as a separator between sections. Use blank lines instead.
        - Use "##" for the main heading: ## Grammar Rule: {rule_title}
        - Use "###" for section headings: ### Rule Statement:, ### Examples:
        - Use "**" for each full target-language example phrase. Inside that
          bold phrase, use "*" only around the adjective itself. Leave the
          native-language translation plain.
        - Use numbered lists (1. 2. ...) for examples.
        - Each numbered example MUST be a single line. Do not put the adjective forms or
          the translation on separate lines: a multi-line item breaks the numbering.
        - Every adjective MUST appear inside a carrier noun phrase in
          {target_language} with its definite article (for example el/la/los/las
          in Spanish). Never list a bare adjective.
        - Mark the adjective itself with "*" italics inside the bold phrase,
          e.g. **el libro *rojo***. The italic hook lets the admin panel
          highlight the adjective in theme color.

        Follow this structure exactly:

        ## Grammar Rule: {rule_title}

        ### Rule Statement:
        [clear explanation of the rule]

        ### Examples:
        Use 4-5 examples. Use a DIFFERENT adjective in each example.
        Do not use only one adjective for all examples, and do not write a sentence
        saying that one adjective will be used for all of them.

        For each example, write one numbered line that shows the form(s) the rule
        is about and a short translation in {native_language}. Keep the whole
        example on that line. Always include the definite article with each carrier
        noun, bold each complete target-language phrase, and keep the "*"
        italics on only the adjective. Do not italicize the translation.

        - For a singular/plural rule, show both forms, e.g.:
          1. **el libro *rojo* / los libros *rojos*** — the red book / the red books
          2. **el dólar *fuerte* / los dólares *fuertes*** — the strong dollar / the strong dollars
        - For a gender rule, pair a masculine and a feminine phrase, e.g.:
          1. **el libro *rojo* / la mesa *roja*** — the red book (masculine) / the red table (feminine)
        - For an agreement rule, show the noun and adjective agreeing, e.g.:
          1. **el libro *rojo* / la mesa *roja*** — the red book / the red table

        Choose adjectives that illustrate the rule clearly, including important spelling,
        agreement, or position patterns.
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

translate_base_words_prompt = PromptTemplate.from_template(
    """
    You are a translation assistant for a language-learning app.
    Translate each of the following base words from {target_language} into
    {native_language}.

    Items:
    {items}

    Return a list with exactly one entry per input item. For each entry, set
    `text` to the item exactly as given (same spelling and case) and
    `translation` to its {native_language} translation. Keep translations
    short and natural. Always provide a real translation — never return the
    source word as its own translation.
    """
)

# Use this prompt for copy-paste purposes inside the chat 
# to check if the generated table is correct
correction_prompt = """
Check the following Markdown table for errors and correct them. Specifically:

1. Fix any missing, broken, or corrupted special characters (e.g., accented letters, diacritics, or other non-ASCII characters that may have been lost or garbled during copy-paste), based on the language used in the table.
2. Check grammar, spelling, and capitalization rules appropriate to the language used in the table (capitalization conventions, verb forms, articles, etc. vary by language — apply the correct rules for whichever language is present).
3. Identify any redundant or duplicate rows that share identical values in key columns (e.g., different labels mapping to the same form or value), and merge them into a single row where appropriate, combining the differing example content (e.g., using "/" to separate multiple examples).
4. Check the table's title/heading for its claimed scope (e.g., "singular", "plural", "present tense", a specific case, a specific set of categories) and verify that every row belonging to that scope is present. If any expected forms are missing, add the missing rows with the correct form, a fitting example sentence, and an explanation consistent in style and language with the existing rows.
5. Preserve the original table structure, formatting, and all substantive content (examples, explanations) — do not remove information, only correct errors, merge truly redundant rows, and add genuinely missing ones.
6. Return the corrected table in the same Markdown format as the input, inside a code block, so it can be copied directly.

Table to check:
<table>
{table_content}
<table>
"""
