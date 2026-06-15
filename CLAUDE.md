# AI Agent Workspace Instructions & Architecture

Welcome, AI Coding Assistant. This workspace is configured with structured architectural guidelines and automated verification pipelines to ensure maximum code quality, security, and Git discipline.

---

## Git Workflow
- NEVER put 'Closes #n' / 'Fixes #n' in commit messages — only in the PR body.
- Always use `gh issue develop <n>` to create issue branches, NOT `git checkout -b`.
- Do NOT add Co-authored-by or any AI attribution lines to commits.

## Environment
- `gh` IS installed and available on this machine — locate the binary (e.g., check PATH) rather than claiming it is unavailable.
- Scripts run under PowerShell 5.1: avoid em-dashes and other non-ASCII chars in scripts, and use `;` not `&&` as the command separator.

## Svelte Conventions
- Files using the `$state` (or other) runes must use the `.svelte.ts` extension, not `.ts`.
- Run svelte-check / type verification after edits when possible before committing.

## Deployment
- Ensure the Dockerfile COPIES migrations and that the dev server is restarted (no stale process) when verifying new endpoints.

---

## Workflow

For non-trivial tasks, follow this sequence:

1. **Plan**: Enter plan mode to explore the codebase and write an implementation plan before coding.
2. **Architect**: Define API schemas, TypeScript types, or Pydantic models before implementing handlers or UI.
3. **Implement**: Write code per the plan, using subagents (Explore, Plan) for large search or design tasks.
4. **Verify**: Run `./scripts/verify-project.ps1` and confirm tests pass before declaring done.

---

## 🚨 CRITICAL CONSTRAINTS & WORKSPACE RULES

Everything is detailed in the [`spec/`](spec/README.md) — Modular project specification (product, architecture, data models, standards).