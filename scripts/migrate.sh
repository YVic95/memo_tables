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

echo "Migrations complete."