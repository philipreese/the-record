# Specification — The Record

Self-hosted music listening history dashboard that aggregates scrobbles from multiple sources into a unified database, with analytics and visualizations.

## Contents

| File | Purpose |
|---|---|
| [product.md](product.md) | Vision, scope, supported sources, non-goals |
| [architecture.md](architecture.md) | Stack, layer map, REST API, sync strategy |
| [data-models.md](data-models.md) | Listen entity, all Pydantic schemas, environment config |
| [standards.md](standards.md) | Git, commit, issue/PR workflow, project board, changelog, code conventions |
| [roadmap.md](roadmap.md) | Remaining phase (multi-tenant auth & privacy) + backlog; Phases 1–3 complete |

## Reading order

- **New to the project?** [product.md](product.md) → [architecture.md](architecture.md) → [data-models.md](data-models.md)
- **Adding a feature?** [architecture.md](architecture.md) (API + layer map) + [data-models.md](data-models.md) (schemas)
- **Changing sync behavior?** [architecture.md](architecture.md#sync-strategy) + [data-models.md](data-models.md#environment-config)
- **Starting new work?** [standards.md](standards.md) — branch naming, commit format, issue/PR flow

## Maintenance

Update the relevant file when behavior changes. Each section ends with a source-of-truth pointer — keep the spec and code in lockstep. Do not describe implementation details that can be read directly from the code; document intent and invariants instead.
