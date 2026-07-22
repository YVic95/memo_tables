-- Enable RLS on language_pairs table (was added later, missed in original RLS migration)
ALTER TABLE language_pairs ENABLE ROW LEVEL SECURITY;

-- Read access for all authenticated users
CREATE POLICY "allow_read_authenticated_language_pairs" ON language_pairs
    FOR SELECT TO authenticated USING (true);

-- Write access restricted to admin role
CREATE POLICY "allow_write_admin_language_pairs" ON language_pairs
    FOR ALL TO authenticated
    USING (auth.jwt() ->> 'role' = 'admin')
    WITH CHECK (auth.jwt() ->> 'role' = 'admin');
