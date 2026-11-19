#!/usr/bin/env bash
set -euo pipefail

root="$1"
out="${GITHUB_OUTPUT:-/dev/stdout}"
name="${root^}"

dir=$(find "$root" -maxdepth 3 -name package.json -not -path '*/node_modules/*' -printf '%h\n' 2>/dev/null | sort | head -1 || true)
if [ -z "$dir" ]; then
  echo "::notice title=${name}::No package.json under ${root}/ yet, nothing to check"
  { echo "dir="; echo "tests=false"; } >> "$out"
  exit 0
fi
echo "Project: $dir"

has_script() { node -e 'process.exit(require(process.argv[1]).scripts?.[process.argv[2]] ? 0 : 1)' "$PWD/$dir/package.json" "$1"; }

missing=()
for script in lint build; do has_script "$script" || missing+=("$script"); done
if [ "${#missing[@]}" -gt 0 ]; then
  echo "::error file=${dir}/package.json,title=${name}::Missing npm script(s): ${missing[*]}. CI runs 'npm run lint' and 'npm run build'."
  exit 1
fi

tests=false
for t in tests test; do
  if [ -d "$dir/$t" ] && [ -n "$(find "$dir/$t" -type f -print -quit)" ]; then tests=true; break; fi
done

if [ "$tests" = true ]; then
  if ! has_script test; then
    echo "::error file=${dir}/package.json,title=${name}::Found a tests folder but no \"test\" npm script"
    exit 1
  fi
  echo "Tests: yes"
else
  echo "::notice title=${name}::No tests yet (no tests/ folder in ${dir}) — lint and build only"
fi

{ echo "dir=$dir"; echo "tests=$tests"; } >> "$out"
