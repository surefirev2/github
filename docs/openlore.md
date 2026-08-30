# OpenLore in this repository

This file is **template-synced** from [`surefirev2/github`](https://github.com/surefirev2/github).
Change OpenLore guidance there; do not long-term fork this doc in application repos.

OpenLore indexes first-party structure so agents can `orient()` without reading the
tree file-by-file. A shareable graph (`.openlore/index-bundle.olbundle`) is committed
so clones and CI bootstrap quickly. The hub `openlore-preflight` hook fails a commit
when that graph is stale relative to in-graph source.

## Required: tune include / exclude (do this first)

**Default configs that leave `includePatterns` / `excludePatterns` empty (or set
`maxFiles` to a huge number) make every freshness rebuild painfully slow.**

Preflight’s slow path re-runs `openlore analyze` against everything the config
admits. Monorepos, vendored trees, generated UI, fixtures, and docs that are not
worth graphing will dominate wall-clock on **every** commit that touches indexed
files until you narrow the scope.

`.openlore/config.json` is **per-repo and never template-synced**. Copy the org
starter from `.github/openlore-config.json` if you do not have one yet, then
**immediately** edit the analysis block for *this* codebase.

### Prefer include (whitelist) over “index everything”

Set `includePatterns` to the directories agents actually navigate (app source,
shared libs, IaC you care about). Empty include means “consider the whole tree
(up to `maxFiles` and built-in ignores).”

```json
{
  "analysis": {
    "maxFiles": 1500,
    "includePatterns": [
      "src/**",
      "server/**",
      "packages/*/src/**",
      "terraform/**"
    ],
    "excludePatterns": [
      "**/node_modules/**",
      "**/.nuxt/**",
      "**/.output/**",
      "**/dist/**",
      "**/coverage/**",
      "**/.venv/**",
      "**/vendor/**",
      "**/generated/**",
      "**/*.min.js",
      "**/fixtures/**",
      "**/testdata/**"
    ]
  }
}
```

### Always exclude junk even if you include

Add `excludePatterns` for build output, package managers, virtualenvs, generated
clients, large fixture corpora, and any subtree you never want in `orient()`
answers. Exclude is additive on top of OpenLore’s built-in pruning; it is not a
substitute for a tight include list on large repos.

### Cap `maxFiles`

Org starters sometimes ship with a high ceiling for CI bootstrapping. For day-to-day
hooks, prefer a few hundred to a few thousand files of **first-party** source—not
`100000`. If analyze hits the cap, tighten includes rather than raising the ceiling.

## After you change the config

```bash
npx --yes openlore@2.1.9 analyze --no-embed --config .openlore/config.json
npx --yes openlore@2.1.9 export bundle
git add -f .openlore/config.json .openlore/index-bundle.olbundle
```

Treat the bundle as generated: regenerate on merge conflicts; never hand-merge it.
See [OpenLore shareable bundles](https://github.com/clay-good/OpenLore/blob/main/docs/shareable-bundle.md).

## What the hub syncs vs what you own

| Path | Owner |
|------|--------|
| `.github/workflows/openlore-*.yml`, `.github/openlore-config.json`, this doc, `.cursor/rules/openlore.mdc` | Hub (template-sync) |
| `.openlore/config.json` | **You** — include / exclude / `maxFiles` / enforcement |
| `.openlore/index-bundle.olbundle` | **You** — refresh after in-graph source or config scope changes |
| `.pre-commit-config.yaml` | **You** — opt into hub hooks; never overwritten by sync |

## First sync bootstrap (required before merge)

Template Sync opens a PR with workflows and this doc. It **never** edits
`.pre-commit-config.yaml`. If the sync also ships `pre-commit-upstream-required.yml`,
that check fails until you add the parent call on the **same** sync PR (or a
follow-up that lands first):

```yaml
  - repo: https://github.com/surefirev2/github
    rev: <pin a hub commit SHA that has .pre-commit-hooks.yaml>
    hooks:
      - id: openlore-preflight
```

Also commit `.openlore/config.json` (tuned includes/excludes — see above) and a
fresh `.openlore/index-bundle.olbundle` before relying on the hook locally or in
CI. Without the opt-in, `automerge-gate/all-passed` stays red on the sync PR.

Upstream reference: [OpenLore configuration](https://github.com/clay-good/OpenLore/blob/main/docs/configuration.md).
