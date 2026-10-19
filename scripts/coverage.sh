#!/usr/bin/env bash
# Write coverage reports for Python and Go to coverage/ and print the totals.
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$ROOT_DIR"
out="$ROOT_DIR/coverage"
mkdir -p "$out"

log "Python coverage"
run_tool pytest -q --cov=scimodel --cov-report=term --cov-report="xml:$out/python.xml" \
  --cov-report="html:$out/python-html" | tail -n 4

if have go; then
  log "Go coverage"
  (cd "$BATCH_DIR" && go test -coverprofile="$out/go.out" ./... >/dev/null \
    && go tool cover -func="$out/go.out" | tail -n 1)
fi
ok "Reports written to $out (python-html/index.html, python.xml, go.out)"
