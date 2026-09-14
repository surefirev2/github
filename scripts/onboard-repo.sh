#!/usr/bin/env bash
# Onboard a repo into the surefirev2 governance perimeter.
# Run from the root of a surefirev2/github checkout.
set -euo pipefail

REPO="${1:-}"
if [[ -z "$REPO" ]]; then
  echo "Usage: $0 <repo-name>" >&2
  exit 1
fi

# Confirm repo exists
if ! gh repo view "surefirev2/$REPO" --json name >/dev/null 2>&1; then
  echo "ERROR: surefirev2/$REPO does not exist" >&2
  exit 1
fi

cd /tmp/github

# Add to repositories list in .github/template-sync.yml
if ! grep -q "^- $REPO\$" .github/template-sync.yml; then
  # Insert before the include_paths line
  sed -i "/^include_paths:/i\\  - $REPO" .github/template-sync.yml
  echo "Added $REPO to template-sync repositories list"
fi

# Add to repo_include_paths
if ! grep -q "^  $REPO:" .github/template-sync.yml; then
  # Append before exclude_paths
  sed -i "/^exclude_paths:/i\\  $REPO:\\n    - .github/workflows/automerge-gate.yml\\n    - .github/workflows/pre-commit-upstream-required.yml\\n" .github/template-sync.yml
  echo "Added $REPO to repo_include_paths"
fi

echo ""
echo "Next steps:"
echo "  1. Update terraform-github/terraform/variables.tf for branch protection"
echo "  2. Push this hub branch and open PR"
echo "  3. After merge, the hub workflow cascades to $REPO"
