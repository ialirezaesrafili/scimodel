#!/usr/bin/env bash
# Shared helpers for SciModel workflow scripts. Source it; do not execute it.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${SCIMODEL_VENV:-$ROOT_DIR/.venv}"
# Used by the scripts that source this file.
# shellcheck disable=SC2034
BATCH_DIR="$ROOT_DIR/batch"
# shellcheck disable=SC2034
BIN_DIR="$ROOT_DIR/bin"

if [[ -t 1 ]]; then
  _bold=$'\033[1m' _green=$'\033[32m' _yellow=$'\033[33m' _red=$'\033[31m' _reset=$'\033[0m'
else
  _bold="" _green="" _yellow="" _red="" _reset=""
fi

log()  { printf '%s==>%s %s\n' "$_bold" "$_reset" "$*"; }
ok()   { printf '%s✔%s %s\n' "$_green" "$_reset" "$*"; }
warn() { printf '%s!%s %s\n' "$_yellow" "$_reset" "$*" >&2; }
die()  { printf '%s✘%s %s\n' "$_red" "$_reset" "$*" >&2; exit 1; }

trap 'die "failed at ${BASH_SOURCE[0]##*/}:${LINENO}: ${BASH_COMMAND}"' ERR

have() { command -v "$1" >/dev/null 2>&1; }

# python_bin prints the interpreter to use: the project venv when present.
python_bin() {
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    printf '%s\n' "$VENV_DIR/bin/python"
  elif have python3; then
    command -v python3
  else
    die "Python 3.11+ is required (python3 not found)."
  fi
}

# run_tool runs a console script from the venv, falling back to `python -m`.
run_tool() {
  local tool="$1"; shift
  if [[ -x "$VENV_DIR/bin/$tool" ]]; then
    "$VENV_DIR/bin/$tool" "$@"
  else
    "$(python_bin)" -m "$tool" "$@"
  fi
}

require_go() {
  have go || die "Go 1.22+ is required for the batch runner (https://go.dev/dl/)."
}

project_version() {
  "$(python_bin)" - "$ROOT_DIR/pyproject.toml" <<'PY'
import sys, tomllib
with open(sys.argv[1], "rb") as handle:
    print(tomllib.load(handle)["project"]["version"])
PY
}
