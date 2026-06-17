-- Enable RLS on all application tables
ALTER TABLE languages ENABLE ROW LEVEL SECURITY;
ALTER TABLE base_words ENABLE ROW LEVEL SECURITY;
ALTER TABLE base_word_topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE topic_translations ENABLE ROW LEVEL SECURITY;
ALTER TABLE word_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE word_translations ENABLE ROW LEVEL SECURITY;
ALTER TABLE word_rule_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE word_forms ENABLE ROW LEVEL SECURITY;
ALTER TABLE word_form_translations ENABLE ROW LEVEL SECURITY;
ALTER TABLE word_form_sentences ENABLE ROW LEVEL SECURITY;
ALTER TABLE grammar_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE grammar_rule_translations ENABLE ROW LEVEL SECURITY;
ALTER TABLE grammar_rule_rows ENABLE ROW LEVEL SECURITY;
ALTER TABLE grammar_rule_row_translations ENABLE ROW LEVEL SECURITY;
ALTER TABLE expressions ENABLE ROW LEVEL SECURITY;
ALTER TABLE expression_translations ENABLE ROW LEVEL SECURITY;
ALTER TABLE expression_topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE sentences ENABLE ROW LEVEL SECURITY;
ALTER TABLE sentence_translations ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_embeddings ENABLE ROW LEVEL SECURITY;

-- Allow read access to all authenticated users (for debugging/testing)
DO $$
DECLARE
    t text;
    tables text[] := ARRAY[
        'languages', 'base_words', 'base_word_topics', 'topics', 'topic_translations',
        'word_categories', 'word_translations', 'word_rule_assignments', 'word_forms',
        'word_form_translations', 'word_form_sentences', 'grammar_rules',
        'grammar_rule_translations', 'grammar_rule_rows', 'grammar_rule_row_translations',
        'expressions', 'expression_translations', 'expression_topics',
        'sentences', 'sentence_translations', 'entity_embeddings'
    ];
BEGIN
    FOREACH t IN ARRAY tables LOOP
        EXECUTE format(
            'CREATE POLICY "allow_read_authenticated_%s" ON %I
             FOR SELECT TO authenticated USING (true)',
            t, t
        );
        EXECUTE format(
            'CREATE POLICY "allow_write_admin_%s" ON %I
             FOR ALL TO authenticated
             USING (auth.jwt() ->> ''role'' = ''admin'')
             WITH CHECK (auth.jwt() ->> ''role'' = ''admin'')',
            t, t
        );
    END LOOP;
END $$;
