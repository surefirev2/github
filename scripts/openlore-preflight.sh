#!/usr/bin/env bash
# OpenLore graph freshness gate for pre-commit (hub-published hook).
#
# Checks that the committed bundle is fresh relative to the working tree
# via OpenLore's preflight command. Does NOT rebuild inline — failing
# means run `make openlore/refresh`.
#
# Recovery: openlore analyze --no-embed && openlore export bundle
# (not --reanalyze by default).
#
# NOTE: In CI (CI=true), this hook is WARNING-ONLY. The OpenLore review
# GitHub Action handles gating separately. This avoids false failures on
# template-sync PRs where the merge ref tree differs from the PR branch.
set -euo pipefail

BUNDLE=.openlore/index-bundle.olbundle
CONFIG=.openlore/config.json
BASE_REF="${OPENLORE_PREFLIGHT_SINCE:-}"

warn() {
  echo "[openlore-preflight] WARNING: $*" >&2
}

refresh_hint() {
  cat >&2 <<EOF

Refresh and stage the shareable index:
  openlore analyze --no-embed --config ${CONFIG}
  openlore export bundle
  git add -f ${BUNDLE}

If analyze is very slow, narrow analysis.includePatterns / excludePatterns and
lower maxFiles in ${CONFIG} first (see docs/openlore.md). Do not raise maxFiles
to paper over a huge tree.

Do not use --reanalyze unless the source fingerprint is unchanged but the index must rebuild.
EOF
}

# In CI, warn only — never fail. The OpenLore review action handles gating.
if [[ "${CI:-}" == "true" ]]; then
  if [[ ! -f "$BUNDLE" ]]; then
    warn "OpenLore bundle missing: ${BUNDLE} (skipped in CI)"
    exit 0
  fi
  if [[ ! -f "$CONFIG" ]]; then
    warn "OpenLore config missing: ${CONFIG} (skipped in CI)"
    exit 0
  fi
  if [[ -n "$BASE_REF" ]]; then
    if [[ "$BASE_REF" == origin/* ]]; then
      branch="${BASE_REF#origin/}"
      git fetch --no-tags --depth=1 origin "$branch" >/dev/null 2>&1 || true
    fi
    openlore preflight --since "$BASE_REF" || warn "OpenLore preflight stale relative to ${BASE_REF} (warning only in CI)"
  else
    openlore preflight || warn "OpenLore preflight stale (warning only in CI)"
  fi
  exit 0
fi

die() {
  echo "$*" >&2
  exit 1
}

if [[ ! -f "$BUNDLE" ]]; then
  die "OpenLore bundle missing: ${BUNDLE}$(refresh_hint)"
fi

if [[ ! -f "$CONFIG" ]]; then
  die "OpenLore config missing: ${CONFIG}
Copy from .github/openlore-config.json or run: openlore init"
fi

if [[ -n "$BASE_REF" ]]; then
  if [[ "$BASE_REF" == origin/* ]]; then
    branch="${BASE_REF#origin/}"
    git fetch --no-tags --depth=1 origin "$branch" >/dev/null 2>&1 || true
  fi
  openlore preflight --since "$BASE_REF" || die "OpenLore preflight failed (stale relative to ${BASE_REF}).$(refresh_hint)"
else
  openlore preflight || die "OpenLore preflight failed.$(refresh_hint)"
fi
