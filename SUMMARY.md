# SF Wizard — Summary

## What we decided

- **Local-first** tool: fast, powerful, and safe for enterprise workflows.
- **Docker-first** distribution, but also runnable **without Docker**.
- **Minimal dependencies** (avoid unnecessary libraries).
- **SF CLI** is the execution backbone (query/deploy/automation).
- UI is **English only**.
- Store **recent org selections** locally (do not depend on SF CLI ordering).

## v0.1.0 scope

**Goal:** a working, testable vertical slice for the Query feature.

Included:
- Monorepo layout (`apps/api`, `apps/web`, `docker`, `data`)
- FastAPI backend:
  - list orgs via `sf org list --json`
  - store/retrieve active org + recents in `data/`
  - run SOQL queries via `sf data query --json`
  - run model + logs + SSE events endpoint
- Vue 3 frontend:
  - header navigation (Query / Deploy)
  - org badge + org picker
  - SOQL editor + run
  - Results table + Logs tab
  - Copy Excel (TSV)
- Docker Compose + Dockerfiles
- Run without Docker instructions

Not included (by design):
- Bulk API mode
- WHERE IN Builder modal (planned next)
- Deployment automation (page is a placeholder in v0.1.0)

## Next versions plan

### v0.1.1 — WHERE IN Builder
- Modal to paste values (Excel/CSV-like)
- Chunking + “execute all chunks” with aggregation
- Better stats (chunks, duration, row count)

### v0.1.2 — Deploy page skeleton
- Parse and analyze `package.xml`
- Detect monolithic metadata (Custom Labels / Translations)
- Create a “deployment plan” (retrieve/merge/deploy steps) + logs

### v0.1.3+ — Deploy actions
- Baseline retrieve (source/target)
- Merge for Custom Labels / Translations
- Validate/deploy runs
- Permission trimming (“pruning”) integration

## Longer-term
- Resume runs
- Chrome extension UI + local agent bridge
- CI/CD-friendly export/import of run plans
