#!/usr/bin/env bash
set -uo pipefail

cd "$(dirname "$0")/.."

outdir=".check-output"
rm -rf "$outdir"
mkdir -p "$outdir"

checks="ruff-check ruff-format pytest tsc eslint vitest"

echo "Running 6 checks in parallel... (logs → .check-output/)"
echo ""

run_and_report() {
  local name="$1"; shift
  local start_s=$(date +%s)
  if "$@" > "$outdir/$name.log" 2>&1; then
    echo "  PASS  $name  ($(($(date +%s) - start_s))s)"
  else
    echo "  FAIL  $name  ($(($(date +%s) - start_s))s)  → .check-output/$name.log"
    echo "FAIL" > "$outdir/$name.exit"
  fi
}

run_and_report "ruff-check"  bash -c "cd backend && uv run ruff check ." &
run_and_report "ruff-format" bash -c "cd backend && uv run ruff format --check ." &
run_and_report "pytest"      bash -c "cd backend && uv run pytest -x -q" &
run_and_report "tsc"         bash -c "cd frontend && npx tsc --noEmit" &
run_and_report "eslint"      bash -c "cd frontend && npx eslint . --max-warnings 0" &
run_and_report "vitest"      bash -c "cd frontend && npx vitest run" &

wait

echo ""

# Print failure details
failed=0
for check in $checks; do
  if [ -f "$outdir/$check.exit" ]; then
    failed=1
    echo "─── FAIL: $check ───"
    tail -25 "$outdir/$check.log"
    echo ""
  fi
done

if [ $failed -eq 1 ]; then
  echo "Some checks failed! Full logs: .check-output/<name>.log"
  exit 1
else
  echo "All 6 checks passed!"
  rm -rf "$outdir"
fi
