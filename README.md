# surefirev2/github

Org automation hub for distributing shared GitHub Actions workflows via
[`surefirev2/repo-sync-action`](https://github.com/surefirev2/repo-sync-action).

This repo is also the **reference OpenLore install**: local pre-commit hooks,
SHA-pinned Actions, and advisory OpenLore analyze/enforce/review — the same
shape application repos should use.

## How changes ship

1. Open a **PR against this hub** (`surefirev2/github`).
2. On merge to `main` (or `workflow_dispatch` of **Template Sync**),
   [`repo-sync-action`](https://github.com/surefirev2/repo-sync-action) opens/updates
   PRs in each repo listed in [`.github/template-sync.yml`](.github/template-sync.yml).
3. Review and merge those **downstream** PRs (do not hand-edit the synced files
   long-term — change them here and re-sync).

Do **not** open one-off PRs in target repos for files owned by this hub.

## Local setup

Requires **Node.js 22.13+** (`node:sqlite`) and Python 3.12+ with
[`pre-commit`](https://pre-commit.com/).

```bash
make init    # pre-commit install && openlore@2.1.9 install --preset full
make check   # pre-commit run --all-files
```

`make init` wires Cursor / `AGENTS.md` managed OpenLore blocks and builds the
local index (gitignored). Confirm with `openlore@2.1.9 doctor`.

Do not skip hooks with `git commit --no-verify`.

## CI

|| Workflow | Role | Merge gate |
|----------|------|------------|
| `pre-commit.yaml` | YAML/actionlint, semantic PR titles, **CI Success** | required |
| `openlore-ci.yml` | `openlore analyze` + `enforce` (advisory findings) | required |
| `openlore-review.yml` | sticky structural PR comment | advisory (ignored by automerge-gate) |
| `pre-commit-upstream-required.yml` | downstream must opt into hub pre-commit hooks | required on opted-in targets |
| `automerge-gate.yml` | `automerge-gate/all-passed` waits for required checks | required |
| `sync.yaml` | template-sync to downstream repos via PR | not a quality gate |

OpenLore **freshness** is enforced by the `openlore-preflight` **pre-commit** hook
(published from this repo). The synced GHA only checks that downstream
`.pre-commit-config.yaml` includes a parent call to this hub — it never
overwrites that file.

Actions are pinned to immutable commit SHAs. Dependabot proposes weekly SHA bumps.

## What gets synced

`repo-sync-action` **opens PRs** in targets. It does not push to the target
default branch.

| Path | Targets |
|------|---------|
| `.github/workflows/openlore-review.yml` | custos, hockeymind, math-desktop, math_spike2, surefire-dms |
| `.github/workflows/openlore-ci.yml` | same |
| `.github/openlore-config.json` | same (CI fallback; does not overwrite `.openlore/config.json`) |
| `.cursor/rules/openlore.mdc` | same |
| `docs/openlore.md` | same (tune include/exclude — required for fast preflight) |
| `.github/workflows/automerge-gate.yml` | same |
| `.github/workflows/pre-commit-upstream-required.yml` | hockeymind, math-desktop, math_spike2, surefire-dms |

**Never synced:** `.pre-commit-config.yaml`, `AGENTS.md`, `CLAUDE.md`,
`.cursorrules`, `.openlore/config.json`, the OpenLore analysis tree.
The shareable `.openlore/index-bundle.olbundle` is per-repo (commit it locally).

### Downstream opt-in (parent pre-commit call)

Keep your unique hooks. Add:

```yaml
  - repo: https://github.com/surefirev2/github
    rev: <pin a hub commit SHA or tag that has .pre-commit-hooks.yaml>
    hooks:
      - id: openlore-preflight
```

Commit `.openlore/config.json` + `.openlore/index-bundle.olbundle` and refresh with
`make openlore/refresh` (or `openlore@2.1.9 analyze --no-embed && openlore export bundle`)
after in-graph changes. **Tune `includePatterns` / `excludePatterns` / `maxFiles`
before a full rebuild** — see the synced [`docs/openlore.md`](docs/openlore.md);
untuned trees make preflight re-analyze painfully slow on every commit.

**First-time sync targets:** Template Sync cannot edit `.pre-commit-config.yaml`.
Add the parent `openlore-preflight` call on the sync PR (see
[`docs/openlore.md`](docs/openlore.md)#first-sync-bootstrap-required-before-merge)
or `pre-commit-upstream-required` / automerge-gate stay red.

After a sync PR lands, each application repo should run `openlore@2.1.9 install`
once locally. hockeymind uses Husky; do not install OpenLore's `.git/hooks`
pre-commit there.

## GitHub App setup (manual)

Template Sync creates an installation token via
[`actions/create-github-app-token`](https://github.com/actions/create-github-app-token)
using `vars.APP_ID` and `secrets.PRIVATE_KEY`.

Org install already in use: **[surefirev2-token-app](https://github.com/organizations/surefirev2/settings/installations/65632433)**
(`app_id` **1237232**, `repository_selection: all`). A push to this hub already
ran Template Sync successfully and opened a barn-league PR, so **org-level**
App credentials are likely already available to Actions. Confirm before changing
anything.

### Verify (read-only)

1. Org installation: [Installations → surefirev2-token-app](https://github.com/organizations/surefirev2/settings/installations/65632433)
2. Org Actions variables (needs org admin): [Organization variables](https://github.com/organizations/surefirev2/settings/variables/actions) — look for `APP_ID` = `1237232`
3. Org Actions secrets (needs org admin): [Organization secrets](https://github.com/organizations/surefirev2/settings/secrets/actions) — look for `PRIVATE_KEY`
4. Or repo overrides on this hub: [github → Variables](https://github.com/surefirev2/github/settings/variables/actions) / [Secrets](https://github.com/surefirev2/github/settings/secrets/actions)

### If missing — configure on this repo (or org)

1. Open the App: [surefirev2-token-app installation](https://github.com/organizations/surefirev2/settings/installations/65632433)
   Ensure it can access `github` and every sync target (`custos`,
   `hockeymind`, `math-desktop`, `math_spike2`, `surefire-dms`).
   App permissions needed: **Contents** read/write, **Pull requests** read/write (and usually **Metadata** read).
2. Get the App ID from [GitHub Apps settings](https://github.com/settings/apps) (or the installation page) — for this org it is **1237232**.
3. Create or download a **private key** for the App (GitHub Apps → your app → Private keys → Generate).
4. Set on **this repository** (or org-wide if that is how `template-template` is wired):
   - Variable `APP_ID` = `1237232` → [Add variable](https://github.com/surefirev2/github/settings/variables/actions)
   - Secret `PRIVATE_KEY` = PEM contents → [Add secret](https://github.com/surefirev2/github/settings/secrets/actions)
5. Re-run sync: [Actions → Template Sync → Run workflow](https://github.com/surefirev2/github/actions/workflows/sync.yaml)
   Prefer **dry_run: true** first, then a real run (or merge a hub PR to `main`).

### Optional hardening

- Prefer `client-id` over deprecated `app-id` in `create-github-app-token` (workflow warns today).
- Keep Dependabot/Renovate pin bumps for `pkgdeps/automerge-gate@v5.0.0` on this hub only.

## Evaluation checklist (barn-league automerge-gate)

After the sync PR merges on barn-league and Terraform requires `automerge-gate/all-passed`:

- [ ] Gate check name is exactly `automerge-gate/all-passed`
- [ ] Enable Auto Merge waits for the gate; gate waits for real CI (`pre-commit`, `check`, …)
- [ ] Intentional red CI blocks auto-merge
- [ ] `ignore-checks` does not drop real required jobs
- [ ] Keep `automerge-gate.yml` on barn-league-hockey only until this passes

## Related

- Terraform hub + protection: https://github.com/surefirev2/terraform-github/pull/176
- Sync-opened pilot PR (not hand-authored): check barn-league for `chore(template): sync from surefirev2/github`
