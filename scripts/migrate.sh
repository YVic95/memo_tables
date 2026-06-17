#!/bin/bash
set -e

# Start Supabase only if not already running
if ! supabase status > /dev/null 2>&1; then
    echo "Starting Supabase..."
    supabase start
else
    echo "Supabase already running, applying new migrations..."
    supabase migration up
fi

echo "Running Alembic migrations..."
uv run alembic upgrade head

# Assign admin role claim to the admin user from .env
if [ -f .env ]; then
    source .env
fi
if [ -n "$ADMIN_EMAIL" ]; then
    echo "Assigning admin role to $ADMIN_EMAIL..."
    supabase db query "UPDATE auth.users SET raw_app_meta_data = raw_app_meta_data || '{\"role\": \"admin\"}'::jsonb WHERE email = '$ADMIN_EMAIL';"
fi

echo "Migrations complete."