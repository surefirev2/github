# surefirev2/github

Org automation hub for distributing shared GitHub Actions workflows via
[`surefirev2/repo-sync-action`](https://github.com/surefirev2/repo-sync-action).

## Current pilot

- **Workflow:** `.github/workflows/automerge-gate.yml` (vendored from
  [`pkgdeps/automerge-gate`](https://github.com/pkgdeps/automerge-gate) `@v5.0.0`)
- **Sync target:** `barn-league-hockey` only (see `.github/template-sync.yml`)

Do **not** widen `repositories` in `template-sync.yml` until the barn-league
pilot evaluation passes.

## Required secrets / vars

Same GitHub App credentials as `template-template`:

| Name | Where | Purpose |
|------|--------|---------|
| `APP_ID` | Actions variable | GitHub App id for `repo-sync-action` |
| `PRIVATE_KEY` | Actions secret | GitHub App private key |

The App needs `contents: write` and `pull-requests: write` on sync targets.

## Sync

Push to `main` or run **Template Sync** (`workflow_dispatch`). Sync opens a PR
in each listed target; it does not push to the target default branch.
