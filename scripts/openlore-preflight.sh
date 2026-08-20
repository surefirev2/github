#!/usr/bin/env bash
# OpenLore graph freshness gate for pre-commit (hub-published hook).
#
# Fast path: import reports verified-current → run preflight.
# Slow path: import would rebuild (e.g. sourceCommit SHA skew) → re-export and
# compare graph content attestation to the committed bundle (ignore commit id).
# Forgetting to refresh after real source changes fails the content compare.
#
# Recovery: analyze --no-embed && export bundle (not --reanalyze by default).
set -euo pipefail

BUNDLE=".openlore/index-bundle.olbundle"
PIN="${OPENLORE_NPM_PIN:-openlore@2.1.8}"
# Optional. Default is graph-vs-working-tree (not --since): OpenLore's --since
# mode stays STALE for new in-graph files on a dirty index even after analyze.
BASE_REF="${OPENLORE_PREFLIGHT_SINCE:-}"
CONFIG=".openlore/config.json"

die() {
  echo "$*" >&2
  exit 1
}

refresh_hint() {
  cat >&2 <<EOF

Refresh and stage the shareable index:
  npx --yes ${PIN} analyze --no-embed --config ${CONFIG}
  npx --yes ${PIN} export bundle
  git add -f ${BUNDLE}

Do not use --reanalyze unless the source fingerprint is unchanged but the index must rebuild.
EOF
}

if [[ ! -f "$BUNDLE" ]]; then
  die "OpenLore bundle missing: ${BUNDLE}$(refresh_hint)"
fi

if [[ ! -f "$CONFIG" ]]; then
  die "OpenLore config missing: ${CONFIG}
Copy from .github/openlore-config.json or run: npx --yes ${PIN} init"
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
IMPORT_LOG="${TMP_DIR}/import.log"

set +e
npx --yes "$PIN" import "$BUNDLE" >"$IMPORT_LOG" 2>&1
IMPORT_RC=$?
set -e
cat "$IMPORT_LOG"

if [[ "$IMPORT_RC" -ne 0 ]]; then
  die "OpenLore import failed (exit ${IMPORT_RC}).$(refresh_hint)"
fi

needs_content_check=0
if grep -qiE 'Falling back to a local rebuild|Artifact was built at an ancestor|rebuilding locally so the index is current' "$IMPORT_LOG"; then
  needs_content_check=1
elif ! grep -qiE 'Imported graph bundle|verified current' "$IMPORT_LOG"; then
  needs_content_check=1
fi

if [[ "$needs_content_check" -eq 1 ]]; then
  echo "Import was not verified-current; comparing committed bundle content to a fresh export..." >&2
  CHECK_BUNDLE="${TMP_DIR}/check.olbundle"
  npx --yes "$PIN" analyze --no-embed --config "$CONFIG"
  npx --yes "$PIN" export bundle --out "$CHECK_BUNDLE"
  python3 - "$BUNDLE" "$CHECK_BUNDLE" <<'PY' || die "OpenLore bundle is stale relative to this tree.$(refresh_hint)"
import gzip
import json
import sys
from pathlib import Path

def load_envelope(path: str) -> dict:
    return json.loads(gzip.decompress(Path(path).read_bytes()).decode("utf-8"))

def attestation_fingerprint(env: dict) -> dict:
    """Compare OpenLore integrity attestation only.

    Full payload bytes (e.g. call-graph.db page size) can differ across
    re-exports even when the graph content digest is identical.
    """
    manifest = env.get("manifest") or {}
    attestation = manifest.get("attestation")
    if not isinstance(attestation, dict):
        raise SystemExit("bundle missing manifest.attestation")
    # Keep only stable integrity fields.
    committed = attestation.get("committed")
    return {
        "attestationVersion": attestation.get("attestationVersion"),
        "schemaVersion": attestation.get("schemaVersion"),
        "committed": committed,
        "digest": attestation.get("digest"),
    }

committed = attestation_fingerprint(load_envelope(sys.argv[1]))
fresh = attestation_fingerprint(load_envelope(sys.argv[2]))
if committed != fresh:
    print("Committed bundle attestation does not match a fresh export of this tree.", file=sys.stderr)
    print(f"  committed={committed}", file=sys.stderr)
    print(f"  fresh={fresh}", file=sys.stderr)
    sys.exit(1)
print("OK: committed OpenLore bundle attestation matches fresh analyze+export")
PY
fi

if [[ -n "$BASE_REF" ]]; then
  if [[ "$BASE_REF" == origin/* ]]; then
    branch="${BASE_REF#origin/}"
    git fetch --no-tags --depth=1 origin "$branch" >/dev/null 2>&1 || true
  fi
  npx --yes "$PIN" preflight --since "$BASE_REF" || die "OpenLore preflight failed.$(refresh_hint)"
else
  npx --yes "$PIN" preflight || die "OpenLore preflight failed.$(refresh_hint)"
fi
