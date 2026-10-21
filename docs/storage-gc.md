# Storage GC

Org-wide prune for **Actions artifacts** and **GitHub Packages**, composed from
maintained Actions / `gh` extensions (not bespoke retention logic).

Workflow: [`.github/workflows/storage-gc.yml`](../.github/workflows/storage-gc.yml)

## When it runs

- Weekly cron (Sunday 06:30 UTC) — **apply**
- `workflow_dispatch` — `dry_run` defaults to **true**

Auth: hub GitHub App (`APP_ID` / `PRIVATE_KEY`), same pattern as template sync.

The App installation must allow **Packages: Read and write** (includes version
delete). A user `GH_TOKEN` with only `read:packages` cannot prune npm/GHCR
locally — use the workflow (App token) or a PAT with `delete:packages`.

## What it uses

| Surface | Tool | Policy (space-first) |
|---------|------|----------------------|
| Actions artifacts | [`andyfeller/gh-artifact-purge`](https://github.com/andyfeller/gh-artifact-purge) | Older than **3 days**; purge expired |
| npm (`math-spike2`) | [`actions/delete-package-versions`](https://github.com/actions/delete-package-versions) | Keep **5** newest versions |
| GHCR | [`dataaxiom/ghcr-cleanup-action`](https://github.com/dataaxiom/ghcr-cleanup-action) | Keep few tagged; delete untagged; exclude `latest`/`main` where set |

`actions/delete-package-versions` has no dry-run; that step is skipped when `dry_run=true`.

## Producer hygiene

- Prefer `retention-days` on `actions/upload-artifact` (1 day for CI handoffs, ≤7 for failure dumps).
- Org admin: Settings → Actions → General → **Artifact and log retention** → **7 days**.

## Local dry-run / apply

```bash
gh extension install andyfeller/gh-artifact-purge
gh artifact-purge surefirev2 3 --purge-expired          # dry-run
gh artifact-purge surefirev2 3 --purge-expired --run    # apply
```

npm / GHCR apply via the workflow (or GitHub UI / Packages API) after merge.
