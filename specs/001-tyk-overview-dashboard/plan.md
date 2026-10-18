# Implementation Plan: Tyk Overview Dashboard

**Branch**: `001-tyk-overview-dashboard` | **Date**: 2026-10-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-tyk-overview-dashboard/spec.md`

## Summary

A small read-only Streamlit dashboard that loads every API definition and organization from the
Tyk Dashboard's MongoDB into one in-memory snapshot per refresh, classifies each API into exactly
one API type, one or more authentication methods and the optional middleware it enables, resolves organization names, and renders
Plotly breakdowns. Clicking a bar adds an AND-combined filter; the filtered API list and per-API
detail panel are the drill-down. Classification is pure, unit-tested Python (`classify.py`) so
every count is traceable and verifiable. Research against the live local data (6,519 APIs) fixed
the classification rules; see [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12 (container image); developed against 3.12+

**Primary Dependencies**: Streamlit (>=1.40, for `on_select` chart events), Plotly, PyMongo, pandas
(already a Streamlit dependency, used for tabular filtering)

**Storage**: Existing MongoDB (Tyk Dashboard database `tyk_analytics`: `tyk_apis` and
`tyk_organisations`), accessed read-only. No application storage.

**Testing**: pytest with JSON fixtures; an opt-in integration test against a real MongoDB

**Target Platform**: Linux Docker container on the internal network

**Project Type**: Single web application (Streamlit)

**Performance Goals**: Overview visible within 15 s for 10,000 API definitions (SC-005). Measured
local data is 6,519 APIs.

**Constraints**: Read-only credentials; no secrets in logs, UI or image; no cache beyond the
per-session snapshot; fetch only the fields needed (projection), never whole `oas_doc` bodies.

**Scale/Scope**: ~10k API definitions, ~tens of organizations, a few concurrent internal viewers

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | How the plan satisfies it |
|---|---|---|
| I. Read-Only by Design | Pass | Source layer exposes only `find`-style reads; docs require a MongoDB user with the `read` role only; a test asserts no write method is reachable and an opt-in test asserts a read-only user is rejected on write. |
| II. Useful High-Level Analytics | Pass | Overview of API type, authentication, middleware, organization computed from stored data only. |
| III. Curated Semantics, Traceable Results | Pass | Explicit rules in `contracts/classification-rules.md`; each API carries the raw evidence behind its classification; unknown states are separate categories. |
| IV. Focused Exploration | Pass | Fixed set of dimensions, no query box, no raw document browser; detail panel shows classification evidence only. |
| V. Transparent Coverage | Pass | Coverage indicator counts APIs with "not understood" or "unmatched" values. |
| VI. Fresh Data on Refresh | Pass | Snapshot built on first open and on explicit Refresh; held in session state; errors never fall back to a previous snapshot shown as current. |
| VII. Simple Python-First | Pass | Streamlit + Plotly, one package, no extra services. A single `ApiSource` protocol is the only abstraction (needed for tests and the stated future-source consideration). |
| VIII. Secure Internal Deployment | Pass | `MONGO_URI` from environment/secret; URI redacted in errors; no app login. |
| IX. Docker Packaging | Pass | Multi-stage-free slim image, non-root user, env-only configuration, pinned dependencies. |
| X. Testing & Maintainability | Pass | Unit tests on classification/aggregation/filtering using fixtures drawn from observed shapes; no production data in tests. |
| XI. Justified Exceptions | N/A | No exceptions needed. |

Post-design re-check: still passes. The design adds no service, cache layer or database.

## Project Structure

### Documentation (this feature)

```text
specs/001-tyk-overview-dashboard/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── classification-rules.md
│   ├── source-access.md
│   └── ui-behavior.md
└── tasks.md             # created later by /speckit-tasks
```

### Source Code (repository root)

```text
src/tyk_analyzer/
├── __init__.py
├── config.py            # settings from environment; URI redaction
├── source.py            # ApiSource protocol + read-only MongoApiSource
├── classify.py          # pure: api type, authentication, organization, coverage
├── snapshot.py          # build Snapshot (records + organizations + load time) from a source
├── filters.py           # AND-combined selections, per-dimension counts
├── charts.py            # Plotly figures from counts
└── app.py               # Streamlit entry point

tests/
├── fixtures/            # small JSON documents per API type / auth / edge case
├── unit/                # classify, filters, snapshot, config redaction, read-only guard
└── integration/         # opt-in (needs MONGO_URI): real read, write rejected for read-only user

Dockerfile
pyproject.toml
.env.example
```

**Structure Decision**: Single Python project with a `src/` layout. `app.py` only wires UI;
all logic lives in pure modules so it can be tested without Streamlit or MongoDB.

## Complexity Tracking

No constitution violations to justify.
