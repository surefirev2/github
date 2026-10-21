# Storage GC

Org-wide prune for **Actions artifacts** and **GitHub Packages** (npm + containers).

Workflow: [`.github/workflows/storage-gc.yml`](../.github/workflows/storage-gc.yml)
Script: [`scripts/storage_gc.py`](../scripts/storage_gc.py)

## When it runs

- Weekly cron (Sunday 06:30 UTC) — **apply** mode
- `workflow_dispatch` — `dry_run` defaults to **true**

Uses the hub GitHub App token (`APP_ID` / `PRIVATE_KEY`), same pattern as template sync.

## npm keep policy

Against the latest published `MAJOR.MINOR.PATCH`:

1. Within each minor, keep only the highest patch.
2. Within each major, keep only the latest two minors (`Y` and `Y-1`).
3. Never delete the single newest version overall.

Example at `1.62.1`: keep `1.62.1` and newest `1.61.x`; delete `1.62.0` and everything `≤ 1.60.*`.

## Containers

Keep digests tagged `latest` or `main`, keep the newest digest, and any other tagged digests. Delete **untagged** older digests.

## Artifacts

Delete artifacts older than **3 days**. Skip artifacts younger than **1 day** (in-flight e2e/Pages).

## Manual org setting

Settings → Actions → General → **Artifact and log retention** → **7 days** (requires org admin).

## Local

```bash
python3 scripts/test_storage_gc.py
GH_TOKEN=$(gh auth token) python3 scripts/storage_gc.py --dry-run
GH_TOKEN=$(gh auth token) python3 scripts/storage_gc.py --apply --package math-spike2
```
