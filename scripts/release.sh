#!/usr/bin/env bash
# Prepare a release: verify a clean tree, run the full gate, build artifacts, and tag.
#   scripts/release.sh            dry run (no tag)
#   scripts/release.sh --tag      create an annotated git tag v<version>
# Pushing the tag (git push origin v<version>) triggers .github/workflows/release.yml.
# shellcheck source=scripts/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$ROOT_DIR" || exit 1

create_tag=0
[[ "${1:-}" == "--tag" ]] && create_tag=1

version="$(project_version)"
package_version="$("$(python_bin)" -c 'import scimodel; print(scimodel.__version__)')"
[[ "$version" == "$package_version" ]] \
  || die "version mismatch: pyproject $version vs scimodel.__version__ $package_version"
grep -q "## \[$version\]" CHANGELOG.md || die "CHANGELOG.md has no entry for [$version]"
[[ -z "$(git status --porcelain)" ]] || die "working tree is not clean"

scripts/check.sh
scripts/build.sh --cross
"$(python_bin)" -m pip install --quiet twine
"$(python_bin)" -m twine check dist/*.whl dist/*.tar.gz

if (( create_tag )); then
  git rev-parse "v$version" >/dev/null 2>&1 && die "tag v$version already exists"
  git tag -a "v$version" -m "SciModel $version"
  ok "Tagged v$version. Publish with: git push origin v$version"
else
  ok "Release $version is ready (dry run). Re-run with --tag to create the tag."
fi
