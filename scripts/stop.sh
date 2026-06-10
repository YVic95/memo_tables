#!/bin/zsh
set -e

echo "Stopping backend (uvicorn)..."
pkill -f "uvicorn serve:app" || echo "Backend was not running."

echo "Stopping Supabase..."
supabase stop

echo "Done."
