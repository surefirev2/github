#!/usr/bin/env bash
# OpenLore graph freshness gate for pre-commit (hub-published hook).
#
# Checks that the committed bundle is fresh relative to the working tree
# via OpenLore's preflight command. Does NOT rebuild inline — failing
# means run `make openlore/refresh`.
#
# Recovery: openlore analyze --no-embed && openlore export bundle
# (not --reanalyze by default).
set -euo pipefail

BUNDLE=.openlore/index-bundle.olbundle
CONFIG=.openlore/config.json
BASE_REF="${OPENLORE_PREFLIGHT_SINCE:-}"

die() {
  echo "$*" >&2
  exit 1
}

refresh_hint() {
  cat >&2 <<EOF

Refresh and stage the shareable index:
  openlore analyze --no-embed --config ${CONFIG}
  openlore export bundle
  git add -f ${BUNDLE}

Do not use --reanalyze unless the source fingerprint is unchanged but the index must rebuild.
EOF
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
