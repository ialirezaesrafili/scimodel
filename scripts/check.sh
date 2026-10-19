#!/usr/bin/env bash
# Quality gate run locally and in CI. Fails on the first problem.
#   scripts/check.sh            everything (Python, Go, shell)
#   scripts/check.sh python     Python only     scripts/check.sh go      Go only
#   scripts/check.sh shell      shell scripts only
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$ROOT_DIR" || exit 1

target="${1:-all}"

check_python() {
  log "ruff format --check"; run_tool ruff format --check src tests examples
  log "ruff check";          run_tool ruff check src tests examples
  log "mypy (strict)";       run_tool mypy
  log "pytest with coverage gate"
  run_tool pytest --cov=scimodel --cov-report=term-missing:skip-covered --cov-fail-under=85 -q
  ok "Python checks passed"
}

check_go() {
  require_go
  (
    cd "$BATCH_DIR" || exit 1
    log "gofmt"
    unformatted="$(gofmt -l .)"
    [[ -z "$unformatted" ]] || die "gofmt needed for: $unformatted"
    log "go vet";  go vet ./...
    log "go test -race"; go test -race -cover ./...
  )
  ok "Go checks passed"
}

check_shell() {
  log "bash -n scripts/*.sh"
  for script in scripts/*.sh; do bash -n "$script"; done
  if have shellcheck; then
    log "shellcheck"; shellcheck -x scripts/*.sh
  else
    warn "shellcheck not installed; syntax-only check performed"
  fi
  ok "Shell checks passed"
}

case "$target" in
  all)    check_shell; check_python; if have go; then check_go; else warn "Go not installed; skipping Go checks"; fi ;;
  python) check_python ;;
  go)     check_go ;;
  shell)  check_shell ;;
  *)      die "unknown target '$target' (use: all, python, go, shell)" ;;
esac
