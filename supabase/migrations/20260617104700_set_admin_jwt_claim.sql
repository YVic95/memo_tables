-- Function to assign admin role claim to a user by email.
-- The initial admin is assigned via migrate.sh using ADMIN_EMAIL from .env.
-- Usage: SELECT assign_admin_role('user@example.com');
CREATE OR REPLACE FUNCTION assign_admin_role(user_email text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    UPDATE auth.users
    SET raw_app_meta_data = raw_app_meta_data || '{"role": "admin"}'::jsonb
    WHERE email = user_email;
END;
$$;
