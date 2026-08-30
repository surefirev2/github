# Agent instructions — surefirev2/github

This is the org automation hub. It distributes shared GitHub Actions via
`surefirev2/repo-sync-action`. It is YAML + docs, not an application runtime.

## Local setup

Requires Node.js 22.13+ and Python 3.12+ with `pre-commit`.

```bash
make init    # pre-commit install + openlore install --preset full
make check   # pre-commit run --all-files
```

Do **not** use `git commit --no-verify`. CI is authoritative; local hooks exist
so agents fail fast before push.

## What is syncable vs local-only

**Template-synced** (unique filenames, additive, safe to land via PR):

- `.github/workflows/openlore-review.yml`
- `.github/workflows/openlore-ci.yml`
- `.github/openlore-config.json` (CI fallback if a repo has no local config)
- `.cursor/rules/openlore.mdc`
- `docs/openlore.md` (tune include/exclude for fast analyze/preflight)
- `.github/workflows/automerge-gate.yml` (all sync targets)
- `.github/workflows/pre-commit-upstream-required.yml` (hockeymind, math-desktop, math_spike2, surefire-dms)

**Never sync** (per-repo):

- `.pre-commit-config.yaml` (downstream must *opt in* with a parent `repos:` entry)
- `AGENTS.md` / `CLAUDE.md` / `.cursorrules`
- `.openlore/config.json`
- the OpenLore index under `.openlore/analysis/`

OpenLore freshness is the `openlore-preflight` pre-commit hook (see
`.pre-commit-hooks.yaml`). Refresh the committed bundle with `make openlore/refresh`.
The synced GHA only fails if a target repo’s pre-commit config lacks the hub
parent call — it never overwrites that file.

## OpenLore

Call `orient()` at the start of a task when the MCP server is wired. Governance
is **advisory** until a finding is mapped to `blocking` in `.openlore/config.json`.
No API key is required for analyze / enforce / review.

Pinned CLI: `openlore@2.1.9`.

<!-- BEGIN OPENLORE (managed — edits inside this block will be overwritten) -->
<!-- openlore-fingerprint: 25cdd746ebf39b56 -->
This project uses OpenLore for persistent architectural memory.

ALWAYS call `orient()` (via the openlore MCP server, or `npx openlore orient --json`)
before reading source files when starting a new task. This returns the relevant
functions, callers, spec sections, and insertion points for the task at hand —
one structural lookup instead of file-by-file rediscovery.

OpenLore prefixes tool responses with a brief, factual freshness note (the
Epistemic Lease) once your cached context has aged or the repo has moved since
your last `orient()`. It is informational — re-`orient()` if you are relying on
cached cross-module structure; otherwise carry on.

For the MCP setup, ensure `openlore mcp` is configured as an MCP server.
See https://github.com/clay-good/OpenLore for details.
<!-- END OPENLORE -->
