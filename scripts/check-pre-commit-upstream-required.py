import sys
from pathlib import Path
import yaml

config_path = Path(".pre-commit-config.yaml")
needle = "github.com/surefirev2/github"
hook_id = "openlore-preflight"
if not config_path.is_file():
    print(f"Missing {config_path}", file=sys.stderr)
    sys.exit(1)
data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
repos = data.get("repos") or []

def normalize(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    if u.endswith(".git"):
        u = u[:-4]
    return u.lower()

matches = []
for entry in repos:
    if not isinstance(entry, dict):
        continue
    repo = str(entry.get("repo") or "")
    if needle not in normalize(repo) and needle not in repo.lower():
        continue
    rev = entry.get("rev")
    ids = [
        str(h.get("id"))
        for h in (entry.get("hooks") or [])
        if isinstance(h, dict) and h.get("id")
    ]
    matches.append((repo, rev, ids))
if not matches:
    print(
        "FAIL: .pre-commit-config.yaml must opt into https://github.com/surefirev2/github\n"
        "Keep your unique hooks and add:\n\n"
        "  - repo: https://github.com/surefirev2/github\n"
        "    rev: <hub SHA or tag with .pre-commit-hooks.yaml>\n"
        "    hooks:\n"
        f"      - id: {hook_id}\n",
        file=sys.stderr,
    )
    sys.exit(1)
ok = False
errors = []
for repo, rev, ids in matches:
    if rev is None or str(rev).strip() == "":
        errors.append(f"{repo}: missing rev")
        continue
    if str(rev).strip().lower() in {"main", "master", "head"}:
        errors.append(f"{repo}: floating rev {rev!r}")
        continue
    if hook_id not in ids:
        errors.append(f"{repo}@{rev}: missing hook {hook_id}")
        continue
    ok = True
if not ok:
    print("FAIL:\n- " + "\n- ".join(errors), file=sys.stderr)
    sys.exit(1)
print(f"OK: opts into surefirev2/github hook {hook_id!r}")
