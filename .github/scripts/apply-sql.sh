#!/usr/bin/env bash
set -euo pipefail

for folder in "$@"; do
  for f in $(find "$folder" -maxdepth 1 -name '*.sql' 2>/dev/null | sort); do
    echo "Applying $f"
    psql -v ON_ERROR_STOP=1 -q -f "$f"
  done
done
