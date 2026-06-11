# Standards — The Record

> Part of the [modular specification](README.md).

## Git & branch conventions

Never commit directly to `main`. All work happens on a purpose-prefixed branch.

| Prefix | Use |
|---|---|
| `feat/` | New feature |
| `fix/` | Bug fix |
| `refactor/` | Code restructure with no behavior change |
| `docs/` | Documentation only |
| `test/` | Tests only |
| `chore/` | Maintenance (config, tooling, CI) |

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
gh issue develop <n> --checkout --name "<prefix>/issue-<n>-brief-title"

# 3. Implement and commit

# 4. Open PR — include "Closes #<n>" so merge auto-closes the issue
gh pr create --fill
```

Always include `Closes #<n>` in the **PR body** (not in commit messages). Merging the PR auto-closes the issue and moves its board card to Done.

## Project board setup

Project: **The Record** — https://github.com/users/philipreese/projects/2

Two automations must be enabled under the project's **Settings → Workflows**:

| Automation | Trigger | Action |
|---|---|---|
| Auto-add to project | Item added to repository (`is:issue`) | Add to project |
| Item closed | Issue or PR closed | Move to Done |

These run natively via GitHub Projects — no GitHub Actions required.

## Changelog

`CHANGELOG.md` at the repo root follows [Keep a Changelog](https://keepachangelog.com/) + [Semantic Versioning](https://semver.org/).

- Add an entry to `[Unreleased]` for every merged change
- Move entries to a versioned section at release time
- Categories (in order): `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`, `Documentation`

## Code conventions

| Concern | Rule |
|---|---|
| Python typing | All functions annotated; no bare `Any` without justification |
| TypeScript | No `any`; types generated from OpenAPI via `pixi run generate-api-types` |
| Secrets | Store in `.env`; never hardcode; `.env` is gitignored |
| Tests | Run via `pixi run test`; no network calls in unit tests |
| Linting | Run via `pixi run lint` before opening a PR |
