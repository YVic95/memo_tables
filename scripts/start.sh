#!/bin/zsh
set -e

echo "Starting Supabase..."
supabase start

echo "Starting backend..."
uv run uvicorn serve:app --reload
