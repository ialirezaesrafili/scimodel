#!/usr/bin/env bash
# Build release artifacts: Python wheel + sdist and Go batch binaries.
#   scripts/build.sh              wheel, sdist, and a native Go binary in bin/
#   scripts/build.sh --go-only    only the native Go binary
#   scripts/build.sh --cross      also cross-compile Go for linux/darwin/windows (amd64, arm64)
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$ROOT_DIR" || exit 1

go_only=0 cross=0
for arg in "$@"; do
  case "$arg" in
    --go-only) go_only=1 ;;
    --cross)   cross=1 ;;
    -h|--help) sed -n '2,5p' "$0"; exit 0 ;;
    *) die "unknown option: $arg" ;;
  esac
done

version="$(project_version)"

build_go() {
  require_go
  mkdir -p "$BIN_DIR"
  local ldflags="-s -w -X main.version=$version"
  log "Building scimodel-batch $version"
  (cd "$BATCH_DIR" && CGO_ENABLED=0 go build -trimpath -ldflags "$ldflags" \
    -o "$BIN_DIR/scimodel-batch" ./cmd/scimodel-batch)
  ok "bin/scimodel-batch"
  if (( cross )); then
    local target os arch suffix
    for target in linux/amd64 linux/arm64 darwin/amd64 darwin/arm64 windows/amd64; do
      os="${target%/*}" arch="${target#*/}" suffix=""
      [[ "$os" == windows ]] && suffix=".exe"
      (cd "$BATCH_DIR" && CGO_ENABLED=0 GOOS="$os" GOARCH="$arch" go build -trimpath \
        -ldflags "$ldflags" -o "$ROOT_DIR/dist/scimodel-batch-$version-$os-$arch$suffix" \
        ./cmd/scimodel-batch)
      ok "dist/scimodel-batch-$version-$os-$arch$suffix"
    done
  fi
}

if (( ! go_only )); then
  log "Building Python wheel and sdist $version"
  rm -rf "$ROOT_DIR/dist"
  "$(python_bin)" -m pip install --quiet build
  "$(python_bin)" -m build --outdir "$ROOT_DIR/dist" "$ROOT_DIR" >/dev/null
  ok "$(ls "$ROOT_DIR"/dist/*.whl)"
fi
if have go; then build_go; elif (( go_only )); then require_go; else warn "Go not installed; skipping batch runner"; fi
