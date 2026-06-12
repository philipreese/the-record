# AI Agent Workspace Instructions & Architecture

Welcome, AI Coding Assistant. This workspace is configured with structured architectural guidelines and automated verification pipelines to ensure maximum code quality, security, and Git discipline.

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