#!/usr/bin/env bash
# Analyze every dataset under a folder in parallel with the Go batch runner.
#   scripts/batch.sh [folder] [scimodel-batch flags...]
#   scripts/batch.sh ~/lab-data -workers 8 -timeout 5m -args "--time-budget 30"
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

folder="${1:-.}"
[[ $# -gt 0 ]] && shift
[[ -d "$folder" ]] || die "not a folder: $folder"

binary="$BIN_DIR/scimodel-batch"
if [[ ! -x "$binary" || "$binary" -ot "$BATCH_DIR/cmd/scimodel-batch/main.go" ]]; then
  "$ROOT_DIR/scripts/build.sh" --go-only
fi

scimodel_cmd="scimodel"
if [[ -x "$VENV_DIR/bin/scimodel" ]]; then
  scimodel_cmd="$VENV_DIR/bin/scimodel"
elif ! have scimodel; then
  die "scimodel is not installed; run scripts/setup.sh first."
fi

exec "$binary" -root "$folder" -out "$folder/scimodel_reports/batch" -scimodel "$scimodel_cmd" "$@"
