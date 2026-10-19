#!/usr/bin/env bash
# Create the development environment: Python venv with all extras, Go batch binary, git hooks.
#   scripts/setup.sh            full setup
#   scripts/setup.sh --no-go    skip the Go batch runner
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

with_go=1
for arg in "$@"; do
  case "$arg" in
    --no-go) with_go=0 ;;
    -h|--help) sed -n '2,4p' "$0"; exit 0 ;;
    *) die "unknown option: $arg" ;;
  esac
done

have python3 || die "Python 3.11+ is required."
python3 - <<'PY' || die "Python 3.11 or newer is required."
import sys
sys.exit(0 if sys.version_info >= (3, 11) else 1)
PY

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  log "Creating virtual environment in $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi
log "Installing SciModel (editable) with development and optional extras"
"$VENV_DIR/bin/python" -m pip install --quiet --upgrade pip
"$VENV_DIR/bin/python" -m pip install --quiet -e "$ROOT_DIR[dev,all]"
ok "Python environment ready ($("$VENV_DIR/bin/python" --version))"

if (( with_go )); then
  if have go; then
    "$ROOT_DIR/scripts/build.sh" --go-only
  else
    warn "Go not found; skipping the batch runner (install Go 1.22+ to enable it)."
  fi
fi

if [[ -d "$ROOT_DIR/.git" ]] && "$VENV_DIR/bin/python" -m pre_commit --version >/dev/null 2>&1; then
  (cd "$ROOT_DIR" && "$VENV_DIR/bin/python" -m pre_commit install >/dev/null)
  ok "pre-commit hooks installed"
fi
ok "Setup complete. Try: source .venv/bin/activate && cd examples && scimodel"
