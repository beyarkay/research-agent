#!/usr/bin/env bash
set -uo pipefail

cd "$(dirname "$0")/.."

tmpdir=$(mktemp -d)
pids=()

run_check() {
  local name="$1"; shift
  ( "$@" > "$tmpdir/$name.out" 2>&1 && echo "PASS" || echo "FAIL" ) > "$tmpdir/$name.status"
}

run_check "ruff-check"  bash -c "cd backend && uv run ruff check ." &
pids+=($!)
run_check "ruff-format" bash -c "cd backend && uv run ruff format --check ." &
pids+=($!)
run_check "pytest"      bash -c "cd backend && uv run pytest -x -q" &
pids+=($!)
run_check "tsc"         bash -c "cd frontend && npx tsc --noEmit" &
pids+=($!)
run_check "eslint"      bash -c "cd frontend && npx eslint . --max-warnings 0" &
pids+=($!)
run_check "vitest"      bash -c "cd frontend && npx vitest run" &
pids+=($!)

for pid in "${pids[@]}"; do wait "$pid" 2>/dev/null || true; done

failed=0
for f in "$tmpdir"/*.status; do
  name=$(basename "$f" .status)
  status=$(cat "$f")
  if [ "$status" = "FAIL" ]; then
    echo "FAIL: $name"
    cat "$tmpdir/$name.out"
    echo ""
    failed=1
  else
    echo "PASS: $name"
  fi
done

rm -rf "$tmpdir"
if [ $failed -eq 1 ]; then
  echo ""
  echo "Some checks failed!"
  exit 1
else
  echo ""
  echo "All checks passed!"
fi
