---
name: ship-issue
description: Ship a GitHub issue end-to-end — branch, implement, verify, commit, and open a PR following the project's spec conventions.
---

Takes an issue number and drives it from `gh issue develop` through an open PR. Enforces branch naming, conventional commit format, verification gates, and the `Closes #n`-in-PR-body rule.

## Steps

### 1. Branch from the issue

```powershell
gh issue develop <n> --checkout --name "<prefix>/<n>-brief-title"
```

`<prefix>` must be one of: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`. Never use `git checkout -b`.

Then move the board card:

```powershell
.\scripts\set-issue-status.ps1 -Issue <n> -Status "In Progress"
```

### 2. Implement

Read `spec/` before writing code. Define types/schemas before handlers. Make the smallest change that closes the issue.

### 3. Verify

```powershell
.\scripts\verify-project.ps1
```

This runs `pixi run lint` (pyrefly + prettier + eslint + svelte-check) and `pixi run test` (backend + frontend), checks branch naming, and validates the last commit message. All gates must pass before committing.

If `pixi` is not on PATH in the current shell, use the full path:

```powershell
& "$env:USERPROFILE\.pixi\bin\pixi.exe" run lint
& "$env:USERPROFILE\.pixi\bin\pixi.exe" run test
```

Note: on Windows, `prettier --check` flags CRLF line endings. If lint fails only due to line endings, re-run with `--end-of-line auto` to confirm it's cosmetic, but do not suppress the check in CI.

### 4. Commit

Format: `<type>(<scope>): Capitalized description` — imperative mood, no trailing period.

```
feat(frontend): Add artist detail drill-down view
fix(sync): Handle 429 rate limit during backfill pass
```

**Never** include `Closes #n` in the commit message. **Never** add `Co-authored-by` lines.

### 5. Open PR

```powershell
gh pr create --title "<type>(<scope>): Capitalized title" --body "$(cat <<'EOF'
## Summary
- What changed and why

## Test plan
- [ ] `.\scripts\verify-project.ps1` passes
- [ ] Exercised the feature end-to-end

Closes #<n>
EOF
)"
```

`Closes #<n>` must be in the **PR body**, not the commit message or issue body. Merging auto-closes the issue and moves the board card to Done.

### 6. CHANGELOG & versioning

No manual action needed. `release-please` reads conventional commit types on merge to `main` and auto-generates a versioned CHANGELOG entry and bumps the version in `CHANGELOG.md` and `pixi.toml`.

| Commit type | Version bump |
|---|---|
| `feat` | minor |
| `fix`, `perf` | patch |
| `feat!` / `BREAKING CHANGE` | major |
| `docs`, `chore`, `refactor`, `test` | none (appears in changelog only) |

## Checklist before declaring done

- [ ] Branch created with `gh issue develop`, not `git checkout -b`
- [ ] `.\scripts\verify-project.ps1` exits 0
- [ ] Commit message follows `type(scope): Capitalized description` — no `Closes #`, no trailing period
- [ ] No `Co-authored-by` in commit
- [ ] PR body contains `Closes #<n>`
- [ ] No direct commits to `main`
