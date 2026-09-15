-- Enable RLS on chat_sessions and chat_messages tables
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- chat_sessions
CREATE POLICY "allow_read_authenticated_chat_sessions" ON chat_sessions
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "allow_write_admin_chat_sessions" ON chat_sessions
    FOR ALL TO authenticated
    USING (auth.jwt() ->> 'role' = 'admin')
    WITH CHECK (auth.jwt() ->> 'role' = 'admin');

-- chat_messages
CREATE POLICY "allow_read_authenticated_chat_messages" ON chat_messages
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "allow_write_admin_chat_messages" ON chat_messages
    FOR ALL TO authenticated
    USING (auth.jwt() ->> 'role' = 'admin')
    WITH CHECK (auth.jwt() ->> 'role' = 'admin');
