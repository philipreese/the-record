# CI & Release Automation Setup Guide

> Covers everything needed to replicate the automated CI + release-please pipeline from the-record in another repo.  
> Order matters — read all the way through before starting.

---

## What this gives you

- **CI** runs on every PR and every push to `main`: backend tests, type checks, frontend lint
- **Release Please** auto-creates a versioned Release PR on every push to `main`
- **Auto-merge** merges the Release PR as soon as CI passes — no human required
- **GitHub Release + tag** created automatically when the Release PR merges
- **Deploy** only fires after CI passes on `main`

---

## Phase 1 — Create the PAT

Do this first. Everything else depends on it.

### Why a PAT is required

GitHub Actions workflows do not trigger from pushes made by `GITHUB_TOKEN`. If release-please uses `GITHUB_TOKEN` to:
- Create the Release PR → CI won't trigger on it (PR sits forever)
- Enable auto-merge → the merge is attributed to the Actions bot → release-please workflow won't fire after merge (tag/GitHub release never created)

A fine-grained PAT bypasses both constraints because pushes and PR events from a PAT user trigger workflows normally.

### Steps

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**
2. Set **Repository access** to the target repo only
3. Grant these **Repository permissions**:
   - Contents: **Read and write**
   - Pull requests: **Read and write**
4. Generate and copy the token immediately (you can't view it again)
5. Go to the target repo → **Settings → Secrets and variables → Actions → New repository secret**
6. Name: `RELEASE_PLEASE_TOKEN`, value: the token you copied

> If you already have a PAT with these permissions on other repos under your profile, you can reuse it — just add the new repo to its repository access list. If you need to regenerate it, existing repos using it will need the new value updated in their secrets.

---

## Phase 2 — Repo settings

All of these must be done before the first Release PR appears. Release Please fires within seconds of merging the setup PR, so configure these **before** you merge.

### 2a. Allow Actions to create PRs

**Settings → Actions → General → Workflow permissions**  
Enable: ✅ **Allow GitHub Actions to create and approve pull requests**

Without this, release-please can't open the Release PR at all.

### 2b. Enable auto-merge

**Settings → General → Pull Requests**  
Enable: ✅ **Allow auto-merge**

### 2c. Set rebase-only merges (recommended)

**Settings → General → Pull Requests → Merge strategies**  
- ✅ Allow rebase merging  
- ☐ Allow squash merging *(disable)*  
- ☐ Allow merge commits *(disable)*

**Why rebase-only:** squash merging collapses all commits in a PR into one, losing the individual conventional commit types. A PR with both `feat:` and `fix:` commits would only count as one type. Rebase preserves all commits, so release-please can accurately compute whether the next version is a minor or patch bump.

### 2d. Branch protection (set up after Phase 4)

Wait until CI has run at least once on the repo, then:

**Settings → Branches → Add branch protection rule**
- Branch name pattern: `main`
- ✅ Require status checks to pass before merging
- ✅ Require branches to be up to date before merging
- In the search box, type `test` and select the **CI / test** check

> You can type the job name manually (`test`) even before CI has run — GitHub accepts it. The job name comes from the `jobs:` key in `ci.yml`.

---

## Phase 3 — Create the files

All of these go on a branch (never commit directly to `main`).

### 3a. `.github/workflows/ci.yml`

Adjust the steps for your stack. The pixi + Node version below is what the-record uses.

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: prefix-dev/setup-pixi@v0.8.0
        with:
          cache: true

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: frontend/package-lock.json

      - name: Run backend tests
        run: pixi run test

      - name: Check types (pyrefly)
        run: pixi run check-types

      - name: Install frontend dependencies
        run: npm ci
        working-directory: frontend

      - name: Run frontend tests
        run: npm run test
        working-directory: frontend

      - name: Lint frontend (prettier, eslint, svelte-check)
        run: npm run lint
        working-directory: frontend
```

**Important:** keep each check as a separate `run` step, not bundled into one command. GitHub annotates failures per step — separate steps make it obvious whether tests, type checks, or lint failed.

**pyrefly note:** do not put `python-interpreter-path` in `pyrefly.toml`. That setting is Windows-only (`.pixi/envs/default/python.exe` doesn't exist on Linux). Remove it and let pyrefly auto-detect the interpreter from the active pixi environment.

### 3b. `.github/workflows/release-please.yml`

```yaml
name: Release Please

on:
  push:
    branches: [main]

permissions:
  contents: write
  pull-requests: write

jobs:
  release:
    runs-on: ubuntu-latest

    steps:
      - uses: googleapis/release-please-action@v4
        id: release
        with:
          config-file: release-please-config.json
          manifest-file: .release-please-manifest.json
          token: ${{ secrets.RELEASE_PLEASE_TOKEN }}

      - name: Enable auto-merge for Release PR
        if: ${{ steps.release.outputs.pr != '' }}
        run: gh pr merge --auto --rebase --repo "${{ github.repository }}" "${{ fromJSON(steps.release.outputs.pr).number }}"
        env:
          GH_TOKEN: ${{ secrets.RELEASE_PLEASE_TOKEN }}
```

**Critical details:**
- `token` on the release-please action: uses the PAT so the PR it creates triggers CI
- `GH_TOKEN` on the auto-merge step: also uses the PAT so the merge is attributed to the PAT user, which means the push to `main` triggers the next release-please run (which creates the tag and GitHub release)
- `--repo "${{ github.repository }}"`: required because there is no `actions/checkout` step in this workflow; without it `gh` fails with `fatal: not a git repository`
- `fromJSON(steps.release.outputs.pr).number`: `steps.release.outputs.pr` is a JSON object, not a PR number; you must parse it

### 3c. `release-please-config.json`

```json
{
  "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
  "packages": {
    ".": {
      "release-type": "simple",
      "changelog-sections": [
        {"type": "feat",     "section": "Features"},
        {"type": "fix",      "section": "Bug Fixes"},
        {"type": "perf",     "section": "Performance Improvements"},
        {"type": "refactor", "section": "Code Refactoring"},
        {"type": "docs",     "section": "Documentation"},
        {"type": "ci",       "section": "Continuous Integration"},
        {"type": "test",     "section": "Tests"},
        {"type": "chore",    "section": "Miscellaneous"}
      ],
      "extra-files": [
        {
          "type": "toml",
          "path": "pixi.toml",
          "jsonpath": "$.workspace.version"
        }
      ]
    }
  }
}
```

**Critical details:**
- The `packages` block is required. A flat config (top-level `release-type` without `packages`) causes release-please to fail to match the manifest key `"."` and produces no Release PR.
- `extra-files` with `type: toml` and `jsonpath: $.workspace.version` targets the `version` field under `[workspace]` in `pixi.toml`. The generic string updater (`# x-release-please-version` annotation) is not needed and should not be used — the explicit TOML updater is more reliable.
- If your version is at the root of `pixi.toml` (not under `[workspace]`), change jsonpath to `$.version`.

### 3d. `.release-please-manifest.json`

```json
{ ".": "X.Y.Z" }
```

Set `X.Y.Z` to the **current version** of the repo. This tells release-please where history begins — it will only consider commits after the corresponding `vX.Y.Z` git tag.

**Do not leave this at `0.0.0`** — release-please will walk the entire commit history and create a massive Release PR.

### 3e. Existing deploy workflow (optional)

If you have a deploy workflow triggered by `push` to `main`, change it to trigger only after CI passes:

```yaml
on:
  workflow_run:
    workflows: [CI]
    types: [completed]
    branches: [main]
  workflow_dispatch:

jobs:
  build-and-deploy:
    if: ${{ github.event_name == 'workflow_dispatch' || github.event.workflow_run.conclusion == 'success' }}
```

---

## Phase 4 — Bootstrap the version tag

Release-please anchors its commit search to the last git tag matching the version in the manifest. If no matching tag exists, it walks every commit since the beginning of the repo.

```bash
# Tag the current HEAD (or a specific commit) at your current version
git tag vX.Y.Z <commit-sha>
git push origin vX.Y.Z

# Create a matching GitHub release
gh release create vX.Y.Z --title "vX.Y.Z" --notes "Baseline release"
```

The `<commit-sha>` should be the commit that represents the state of the repo at version X.Y.Z — typically the last commit on `main` before your setup branch.

---

## Phase 5 — Open and merge the setup PR

1. Push your branch with all the files from Phase 3
2. Open a PR: `gh pr create --title "ci: Set up CI and release-please automation" ...`
3. CI will run on the PR (this is fine — it won't loop)
4. Get CI green, then merge
5. **Watch immediately**: within ~30 seconds release-please will fire and open the first Release PR

---

## Phase 6 — Verify end-to-end

After merging the setup PR, confirm each stage:

| Stage | What to check |
|---|---|
| Release PR created | A PR titled `chore(main): release X.Y.Z` appears |
| CI triggered on Release PR | GitHub shows a pending `CI / test` check on the Release PR |
| CI passes | The check goes green |
| Auto-merge fires | PR merges automatically within seconds of CI passing |
| Tag + GitHub release created | `gh release list` shows the new version |

If auto-merge doesn't fire, check:
- Is auto-merge enabled in repo settings? (Phase 2b)
- Did the `gh pr merge` step succeed in the release-please run? (check Actions logs)

If CI doesn't trigger on the Release PR:
- Is the PAT being used for the release-please action? (`token: ${{ secrets.RELEASE_PLEASE_TOKEN }}`)
- Does the PAT have Contents + Pull requests write permissions?

If the tag/release isn't created after auto-merge:
- Is the PAT also used for `GH_TOKEN` in the auto-merge step? (not `GITHUB_TOKEN`)
- Check: does the push to `main` show a release-please workflow run in Actions?

---

## Version bump rules

| Commit type | Version bump |
|---|---|
| `feat` | minor (0.x.0) |
| `fix`, `perf` | patch (0.0.x) |
| `BREAKING CHANGE` footer or `!` suffix | major (x.0.0) |
| `docs`, `chore`, `refactor`, `ci`, `test` | no bump (appear in CHANGELOG only) |

---

## Day-to-day workflow

1. Write conventional commits: `feat(scope): ...`, `fix(scope): ...`, etc.
2. Open a PR — CI runs automatically
3. Merge — release-please updates (or creates) the open Release PR
4. When you're ready to ship, the Release PR auto-merges once CI passes
5. GitHub release and tag appear automatically

You never manually update `CHANGELOG.md` or version files.
