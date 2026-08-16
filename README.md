# surefirev2/github

Org automation hub for distributing shared GitHub Actions workflows via
[`surefirev2/repo-sync-action`](https://github.com/surefirev2/repo-sync-action).

## How changes ship

1. Open a **PR against this hub** (`surefirev2/github`).
2. On merge to `main` (or `workflow_dispatch` of **Template Sync**),
   [`repo-sync-action`](https://github.com/surefirev2/repo-sync-action) opens/updates
   PRs in each repo listed in [`.github/template-sync.yml`](.github/template-sync.yml).
3. Review and merge those **downstream** PRs (do not hand-edit the synced files
   long-term — change them here and re-sync).

Do **not** open one-off PRs in target repos for files owned by this hub.

## Current pilot

| Item | Value |
|------|--------|
| Workflow | [`.github/workflows/automerge-gate.yml`](.github/workflows/automerge-gate.yml) |
| Upstream | [`pkgdeps/automerge-gate@v5.0.0`](https://github.com/pkgdeps/automerge-gate) (public mode) |
| Required check name | `automerge-gate/all-passed` |
| Sync target | `barn-league-hockey` **only** |

Do **not** widen `repositories` in `template-sync.yml` until the barn-league
pilot evaluation passes.

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
   Ensure it can access `github` and every sync target (`barn-league-hockey` today).  
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

## Evaluation checklist (barn-league pilot)

After the sync PR merges on barn-league and Terraform requires `automerge-gate/all-passed`:

- [ ] Gate check name is exactly `automerge-gate/all-passed`
- [ ] Enable Auto Merge waits for the gate; gate waits for real CI (`pre-commit`, `check`, …)
- [ ] Intentional red CI blocks auto-merge
- [ ] `ignore-checks` does not drop real required jobs
- [ ] No wider `template-sync.yml` targets until this passes

## Related

- Terraform hub + protection: https://github.com/surefirev2/terraform-github/pull/176
- Sync-opened pilot PR (not hand-authored): check barn-league for `chore(template): sync from surefirev2/github`
