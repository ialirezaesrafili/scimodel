#!/usr/bin/env bash
# End-to-end smoke test: regenerate example data, run discovery on every example, check results.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$ROOT_DIR"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

log "Regenerating synthetic examples"
"$(python_bin)" examples/generate_examples.py
git diff --quiet -- examples/*.csv 2>/dev/null || warn "regenerated examples differ from the committed copies"

scimodel=("$(python_bin)" -m scimodel)
"${scimodel[@]}" scan examples >/dev/null
for dataset in examples/*.csv; do
  name="$(basename "$dataset" .csv)"
  log "discover $name"
  "${scimodel[@]}" discover "$dataset" --json --time-budget 5 --output-dir "$work/$name" \
    > "$work/$name.json"
  "$(python_bin)" - "$work/$name.json" <<'PY'
import json, sys
result = json.load(open(sys.argv[1]))
best = result["candidates"][0]
assert best["fit"]["converged"], "best model did not converge"
assert result["quality"][result["best"]]["grade"] in "ABC", "best model graded D"
print(f"   best={result['best']} R2={best['fit']['metrics']['r_squared']:.4f}")
PY
done
ok "Smoke test passed for $(ls examples/*.csv | wc -l) datasets"
