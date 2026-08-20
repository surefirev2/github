#!/usr/bin/env bash
# Emit config=<path> for GITHUB_OUTPUT (OpenLore CI).
set -euo pipefail
if [[ -f .openlore/config.json ]]; then
  echo "config=.openlore/config.json"
elif [[ -f .github/openlore-config.json ]]; then
  echo "config=.github/openlore-config.json"
else
  echo "No OpenLore config found." >&2
  echo "Commit .openlore/config.json or sync .github/openlore-config.json from surefirev2/github." >&2
  exit 1
fi
