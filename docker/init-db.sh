#!/bin/bash
set -eo pipefail

run_dir() {
    local dir="$1"
    for f in $(ls "$dir"/*.sql 2>/dev/null | sort); do
        echo ">>> Applying $f"
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$f"
    done
}

run_dir /migrations

if [ "${SEED_DB:-false}" = "true" ]; then
    run_dir /seeds
else
    echo ">>> SEED_DB is not 'true', skipping seeds"
fi