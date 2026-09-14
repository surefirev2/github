# Repository Onboarding Guide

A `surefirev2` GitHub repository is "fully onboarded" when it has all of:

1. **Branch protection** on `main` requiring `automerge-gate/all-passed`
2. **automerge-gate** GitHub Actions workflow
3. **OpenLore CI** workflow (analyze + enforce, advisory)
4. **OpenLore review** workflow (sticky PR comment)
5. **pre-commit upstream required** workflow + `.pre-commit-config.yaml` opt-in

This guide covers both **new** repos (added to `terraform-github` for the first time)
and **renamed** repos (already in `terraform-github`, changing name).

---

## Quick checklist

```bash
# Verify repo exists and is visible
gh repo view surefirev2/<repo> --json name,url

# Check current branch protection (if any)
gh api repos/surefirev2/<repo>/branches/main/protection \
  --jq '{enforce_admins: .enforce_admins.enabled, checks: .required_status_checks.contexts}'

# Check CI workflows
gh api repos/surefirev2/<repo>/actions/workflows --jq '.workflows[].name'
```

---

## Three-PR pattern

Every rename or onboarding needs three PRs. Do them in this order.

### PR 1 — `terraform-github` (branch protection + rename)

This is the canonical source for GitHub repository settings.

**If renaming:**

1. Update `terraform/variables.tf`:
   - Change the key in `var.repositories` (e.g. `"terraform-cloudflare"` → `"terraform-cloudflare-surefire"`)
   - Change the `name` field inside that map entry
   - Update `branch_protection_status_checks` to use the new key
2. Add a `moved` block in a new `terraform/moved.tf`:

   ```hcl
   moved {
     from = github_repository.repos["terraform-cloudflare"]
     to   = github_repository.repos["terraform-cloudflare-surefire"]
   }
   ```

   **Without this, Terraform will destroy+create — which destroys the GitHub repo.**
3. Update `scripts/terraform-import-existing.sh` references if the key changed
4. Run `pre-commit run --all-files` (terraform fmt, validate, lockfile in sync)
5. Push to a branch, open PR
6. CI will show the plan — verify it says **"in-place update"**, not "destroy/create"
7. Merge → CI applies branch protection

**If new:**

Add the repo to `var.repositories` and `branch_protection_status_checks` following existing patterns.

### PR 2 — `github` (hub) (template-sync targets)

The hub `surefirev2/github` distributes workflows via `surefirev2/repo-sync-action`.

1. Clone `surefirev2/github` to `/tmp/github`
2. Edit `.github/template-sync.yml`:
   - Add the repo to `repositories:` list
   - Add the repo to `repo_include_paths:` with at minimum:
     - `.github/workflows/automerge-gate.yml`
     - `.github/workflows/pre-commit-upstream-required.yml`
   - `include_paths` (synced to all targets) already covers:
     - `.github/workflows/openlore-ci.yml`
     - `.github/workflows/openlore-review.yml`
     - `.github/openlore-config.json`
     - `scripts/check-pre-commit-upstream-required.py`
     - `scripts/resolve-openlore-config.sh`
     - `docs/openlore.md`
3. Commit and push to a branch, open PR against `main`
4. **Merge → next hub push cascades the workflows into the target repo**

You can also run `scripts/onboard-repo.sh <repo-name>` from the hub checkout to automate steps 2-3.

### PR 3 — Target repo (pre-commit opt-in)

The target repo must opt into `surefirev2/github` hooks.

In the target repo's `.pre-commit-config.yaml`, add:

```yaml
  - repo: https://github.com/surefirev2/github
    rev: <pin to a hub commit SHA with .pre-commit-hooks.yaml>
    hooks:
      - id: openlore-preflight
```

The hub commit SHA must be a commit on `main` that contains `.pre-commit-hooks.yaml`.

Get it: `gh api repos/surefirev2/github/commits/main --jq '.sha'`

Also add `.github/openlore-config.json` (copy from hub — it's the fallback config).

---

## Troubleshooting

### Token scope errors pushing workflow YAMLs

The default `gh` token lacks `workflow` scope. Non-workflow files push fine, but workflow YAMLs fail.

Workaround 1: Push non-workflow files, then add workflow files via GitHub API (requires App token):

```bash
# Push non-workflow files normally
git push origin <branch>

# Add workflow files via GitHub API
GH_TOKEN=$(github-app-token work)
gh api repos/surefirev2/<repo>/contents/.github/workflows/automerge-gate.yml \
  -X PUT \
  -f message="ci: add automerge-gate" \
  -f content="$(base64 -w0 <path/to/automerge-gate.yaml)" \
  -f branch=<branch>
```

Workaround 2: Push non-workflow files, then manually commit the workflow files from an owner's machine.

### Branch protection blocks all PRs after merge

This happens when branch protection requires `automerge-gate/all-passed` but the workflow doesn't exist yet.

Fix: Make sure PR #2 (hub) has been merged and the workflow files have been synced before PR #1 (terraform-github) is applied. If already stuck, temporarily remove branch protection via GitHub UI, let CI re-apply it.

### Terraform plan shows destroy+create instead of in-place update

Missing or incorrect `moved` block. Verify `terraform/moved.tf` has the right `from` (old key) and `to` (new key).

### Template-sync doesn't reach the repo

- Confirm the repo is in `.github/template-sync.yml` `repositories:` list
- Check the hub workflow runs for errors (`gh run list` on hub)
- The target repo must be visible to the GitHub App installation

---

## Post-merge verification

```bash
# Branch protection
gh api repos/surefirev2/<repo>/branches/main/protection \
  --jq '{enforce_admins: .enforce_admins.enabled, checks: .required_status_checks.contexts}'
```

Expected:
- `enforce_admins.enabled` = true
- `checks.contexts` includes `automerge-gate/all-passed`

```bash
# Workflows running
gh api repos/surefirev2/<repo>/actions/workflows --jq '.workflows[].name'
```

Expected: automerge-gate, openlore-ci, openlore-review, pre-commit-upstream-required
