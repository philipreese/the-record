# Standards — The Record

> Part of the [modular specification](README.md).

## Git & branch conventions

Never commit directly to `main`. All work happens on a purpose-prefixed branch.

| Prefix      | Use                                      |
| ----------- | ---------------------------------------- |
| `feat/`     | New feature                              |
| `fix/`      | Bug fix                                  |
| `refactor/` | Code restructure with no behavior change |
| `docs/`     | Documentation only                       |
| `test/`     | Tests only                               |
| `chore/`    | Maintenance (config, tooling, CI)        |

Recommended branch name format: `<prefix>/issue-<n>-brief-title`

## Commit format

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): Capitalized description
```

- **Type**: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`
- **Scope**: optional — e.g. `backend`, `frontend`, `sync`, `spec`
- **Description**: imperative mood, first letter capitalized, no trailing period

Examples:
```
feat(frontend): Add artist detail drill-down view
fix(sync): Handle 429 rate limit during backfill pass
chore(spec): Add standards.md to modular spec
```

## Issue & PR workflow

```bash
# 1. Create an issue
gh issue create --title "..." --body "..."

# 2. Branch from the issue
gh issue develop <n> --checkout --name "<prefix>/<n>-brief-title"

# 3. Move issue to In Progress on the project board
.\scripts\set-issue-status.ps1 -Issue <n> -Status "In Progress"

# 4. Implement and commit

# 5. Open PR — include "Closes #<n>" so merge auto-closes the issue
gh pr create --title "..." --body "..."

# 6. Before merging: add changelog entries under [Unreleased] in CHANGELOG.md
#    release-please owns the version bump and versioned section — no manual release commit
```

Always include `Closes #<n>` in the **PR body** (not in commit messages (or in issue bodies)). Merging the PR auto-closes the issue and moves its board card to Done.

**Project board field IDs** (stable, do not change):

| Field | ID |
|---|---|
| Project node ID | `PVT_kwHOALMvNM4BaahH` |
| Status field ID | `PVTSSF_lAHOALMvNM4BaahHzhVSUB8` |
| Todo option | `f75ad846` |
| In Progress option | `47fc9ee4` |
| In Review option | `ccc97365` |
| Done option | `98236657` |

## Project board setup

Project: **The Record** — https://github.com/users/philipreese/projects/2

Two automations must be enabled under the project's **Settings → Workflows**:

| Automation          | Trigger                               | Action         |
| ------------------- | ------------------------------------- | -------------- |
| Auto-add to project | Item added to repository (`is:issue`) | Add to project |
| Item closed         | Issue or PR closed                    | Move to Done   |

These run natively via GitHub Projects — no GitHub Actions required.

## Changelog & releases

`CHANGELOG.md` at the repo root follows [Keep a Changelog](https://keepachangelog.com/) + [Semantic Versioning](https://semver.org/).

- Add entries to `[Unreleased]` throughout development (one entry per PR is fine)
- Categories (in order): `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`, `Documentation`
- **Do not** manually move entries to a versioned section or commit `docs(changelog): release vX.Y.Z` — release-please owns all of that

### Automated release flow (release-please)

On every push to `main`, `release-please` inspects the conventional commit history since the last tag and either:
- **Updates the open Release PR** (no new version-bumping commits since last update), or
- **Creates / refreshes a Release PR** that moves `[Unreleased]` to a new versioned section and bumps the version in `CHANGELOG.md` and `pixi.toml`

When the Release PR merges (auto-merge is enabled — see below), release-please creates a GitHub release and git tag.

Version bump rules:
| Commit type | Bump |
|---|---|
| `feat` | minor |
| `fix`, `perf` | patch |
| any `BREAKING CHANGE` footer or `!` suffix | major |
| `docs`, `chore`, `refactor`, `ci`, `test` | no bump (appear in CHANGELOG only) |

### Required repo settings

For auto-merge of the Release PR to work, these must be enabled in the repository:
1. **Settings → General → Allow auto-merge** — enables the feature globally
2. **Settings → Branches → Branch protection for `main`** — require the **CI / test** status check to pass before merging

## Code conventions

| Concern       | Rule                                                                     |
| ------------- | ------------------------------------------------------------------------ |
| Python typing | All functions annotated; no bare `Any` without justification             |
| TypeScript    | No `any`; types generated from OpenAPI via `pixi run generate-api-types` |
| Secrets       | Store in `.env`; never hardcode; `.env` is gitignored                    |
| Tests         | Run via `pixi run test`; no network calls in unit tests                  |
| Linting       | Run via `pixi run lint` before opening a PR                              |
