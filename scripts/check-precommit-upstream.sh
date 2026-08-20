#!/usr/bin/env bash
# Fail if .pre-commit-config.yaml does not opt into surefirev2/github hooks.
# Used by .github/workflows/pre-commit-upstream-required.yml (template-synced).
set -euo pipefail

CONFIG="${1:-.pre-commit-config.yaml}"
REQUIRED_REPO_NEEDLE="${REQUIRED_PRECOMMIT_REPO:-github.com/surefirev2/github}"
REQUIRED_HOOK_ID="${REQUIRED_PRECOMMIT_HOOK_ID:-openlore-preflight}"

if [[ ! -f "$CONFIG" ]]; then
  echo "Missing ${CONFIG}" >&2
  echo "This repository must keep a .pre-commit-config.yaml that opts into" >&2
  echo "https://github.com/surefirev2/github (hook id: ${REQUIRED_HOOK_ID})." >&2
  exit 1
fi

python3 - "$CONFIG" "$REQUIRED_REPO_NEEDLE" "$REQUIRED_HOOK_ID" <<'PY'
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

config_path, needle, hook_id = sys.argv[1], sys.argv[2], sys.argv[3]
data = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
repos = data.get("repos") or []

def normalize_repo(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    if u.endswith(".git"):
        u = u[:-4]
    return u.lower()

matches = []
for entry in repos:
    if not isinstance(entry, dict):
        continue
    repo = str(entry.get("repo") or "")
    if needle.lower() not in normalize_repo(repo) and needle.lower() not in repo.lower():
        continue
    rev = entry.get("rev")
    hooks = entry.get("hooks") or []
    ids = []
    for h in hooks:
        if isinstance(h, dict) and h.get("id"):
            ids.append(str(h["id"]))
    matches.append({"repo": repo, "rev": rev, "ids": ids})

if not matches:
    print(
        f"FAIL: {config_path} has no repos entry for {needle}.\n"
        f"Add a parent call (do not replace your existing hooks):\n\n"
        f"  - repo: https://github.com/surefirev2/github\n"
        f"    rev: <pin a hub commit SHA or tag that has .pre-commit-hooks.yaml>\n"
        f"    hooks:\n"
        f"      - id: {hook_id}\n",
        file=sys.stderr,
    )
    sys.exit(1)

ok = False
errors = []
for m in matches:
    rev = m["rev"]
    if rev is None or str(rev).strip() == "":
        errors.append(f"{m['repo']}: missing rev (pin a SHA or tag, not floating main)")
        continue
    rev_s = str(rev).strip().lower()
    if rev_s in {"main", "master", "head"}:
        errors.append(f"{m['repo']}: rev={rev!r} is floating — pin a commit SHA or release tag")
        continue
    if hook_id not in m["ids"]:
        errors.append(f"{m['repo']}@{rev}: hooks missing id {hook_id!r} (have {m['ids']})")
        continue
    ok = True

if not ok:
    print("FAIL: hub pre-commit opt-in is incomplete:\n- " + "\n- ".join(errors), file=sys.stderr)
    sys.exit(1)

print(f"OK: {config_path} opts into surefirev2/github hook {hook_id!r}")
PY
