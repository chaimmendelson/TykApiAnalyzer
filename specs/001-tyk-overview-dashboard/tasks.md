---

description: "Task list for the Tyk Overview Dashboard"
---

# Tasks: Tyk Overview Dashboard

**Input**: Design documents from `/specs/001-tyk-overview-dashboard/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. The spec does not ask for TDD, but constitution Principle X requires tests for classification, aggregation, missing or unrecognized settings, and read-only access. Write each story's tests first and confirm they fail.

**Organization**: Tasks are grouped by user story so each can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1, US2 or US3 (maps to spec.md user stories)
- All paths are relative to the repository root

## Path Conventions

Single Python project with a `src/` layout: `src/tyk_analyzer/`, `tests/unit/`, `tests/integration/`, `tests/fixtures/`. Rules referenced below live in `specs/001-tyk-overview-dashboard/contracts/classification-rules.md` (called "classification rules").

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create the package and test directories from plan.md: `src/tyk_analyzer/__init__.py`, `tests/unit/`, `tests/integration/`, `tests/fixtures/` (add empty `__init__.py` or `conftest.py` only where pytest needs them)
- [X] T002 Create `pyproject.toml` (src layout, package `tyk_analyzer`, Python >=3.12) with runtime dependencies `streamlit>=1.40`, `plotly`, `pymongo`, `pandas`, optional `dev` extra with `pytest` and `ruff`, and a `[tool.ruff]` and `[tool.pytest.ini_options]` section (`testpaths = ["tests"]`, `pythonpath = ["src"]`)
- [X] T003 [P] Create `.env.example` listing `MONGO_URI`, `MONGO_DB`, `TYK_APIS_COLLECTION`, `TYK_ORGS_COLLECTION`, `MONGO_TIMEOUT_MS` with placeholder values only, and create `.gitignore` ignoring `.env`, `__pycache__/`, `.venv/`, `.pytest_cache/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain types, configuration, read-only data source and test fixtures that every story needs

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Create `src/tyk_analyzer/model.py` per data-model.md: enums `ApiType` (REST_CLASSIC, REST_OAS, GRAPHQL, UDG, FEDERATION, MCP, TCP, STREAMING, NOT_UNDERSTOOD), `AuthMethod` (NONE, API_KEY, JWT, BASIC, OAUTH2, OPENID, MUTUAL_TLS, REQUEST_SIGNATURE, CUSTOM_PLUGIN, EXTERNAL_OAUTH, NOT_SET, NOT_UNDERSTOOD), `ActiveState` (ACTIVE, INACTIVE, UNKNOWN), `OrgStatus` (MATCHED, NOT_SET, UNMATCHED); frozen dataclasses `ApiRecord` (fields `id`, `api_id`, `name`, `active`, `api_type`, `tls_enabled`, `auth_methods` as frozenset, `org_id`, `org_label`, `org_status`, `unclassified` as tuple, `evidence` as dict of str to str), `Organization` (`id`, `name`), `Coverage` (`total`, `unclassified_count`, `by_reason`), `Snapshot` (`records`, `organizations`, `loaded_at` as UTC datetime, `coverage`). Constraints, quoted from data-model.md: "`name` and ids are coerced to strings", `name` is an empty string if absent, "any field of unexpected type yields `NOT_UNDERSTOOD` rather than an exception", `Organization.name` is `owner_name` "(falls back to `owner_slug`, then id)", `ApiRecord.id` is `_id` as string and is the unique identity
- [X] T005 [P] Create `src/tyk_analyzer/config.py`: a frozen `Settings` dataclass loaded by `load_settings()` from environment with defaults `MONGO_DB=tyk_analytics`, `TYK_APIS_COLLECTION=tyk_apis`, `TYK_ORGS_COLLECTION=tyk_organisations`, `MONGO_TIMEOUT_MS=5000`; `MONGO_URI` is required (raise a clear `ConfigError` that does not echo any value); add `redact(text, secrets)` that removes the URI, and any user or password parsed from it, from any string
- [X] T006 [P] Create `src/tyk_analyzer/source.py`: `SourceError` exception; `ApiSource` Protocol with `fetch_apis() -> list[dict]` and `fetch_organizations() -> list[dict]`; `MongoApiSource(settings)` implementing only those two public methods using `find` with the explicit projection from contracts/source-access.md (never project `oas_doc.paths`, `graphql.schema`, certificates or secrets); use `serverSelectionTimeoutMS` from settings; wrap every `pymongo` error in `SourceError` with a message passed through `redact` so it never contains the URI, user name or password; never return a partial list on cursor failure; do not import or call any write operation
- [X] T007 [P] Create fixture documents in `tests/fixtures/apis.json` (list of API documents shaped like the real `tyk_apis` documents, flat top level with optional `oas_doc`) with one document per classification-rules row: REST classic, REST OAS, GraphQL proxy-only, UDG (`executionEngine` with `graphql.engine.data_sources`), Federation (`proxyOnly` with `graphql.supergraph.subgraphs`), MCP (OAS with `mcpTools`), Streaming (OAS with `x-tyk-streaming`), TCP, TLS, unknown `protocol`; edge cases: GraphQL `enabled: false` with `execution_mode: proxyOnly`, non-boolean auth flags, missing `name`/`org_id`/`active`, an API with several auth flags, an inactive API, an OAS API whose `securitySchemes` contradict the flags; and `tests/fixtures/organizations.json` with `_id` given as `{"$oid": "..."}` strings. Add `tests/conftest.py` with fixtures that load these files, convert `$oid` values to `bson.ObjectId`, and provide `InMemorySource(apis, orgs)` implementing `ApiSource` (optionally raising `SourceError` on demand)
- [X] T008 [P] Create `tests/unit/test_config.py`: defaults applied, missing `MONGO_URI` raises `ConfigError` whose message contains no URI, and `redact` removes a URI with `user:password@` including the user and password separately
- [X] T009 [P] Create `tests/unit/test_source.py`: using a fake pymongo client injected into `MongoApiSource`, assert (a) the class has no public methods besides `fetch_apis` and `fetch_organizations`, (b) the projection excludes `oas_doc.paths` and `graphql.schema`, (c) a raised `pymongo` error becomes `SourceError` whose message does not contain the URI, user or password, (d) a cursor failing midway raises `SourceError` rather than returning a partial list

**Checkpoint**: Foundation ready. User story work can now begin.

---

## Phase 3: User Story 1 - See how Tyk is used at a glance (Priority: P1) 🎯 MVP

**Goal**: Show the total and breakdowns by API type, authentication method, organization and active state for all API definitions.

**Independent Test**: Load the fixtures (or the local database per quickstart.md) and verify the total and every breakdown match the known data, with each non-authentication breakdown summing to the total.

### Tests for User Story 1 ⚠️

> Write these first and make sure they FAIL before implementation.

- [X] T010 [P] [US1] Create `tests/unit/test_classify_api_type.py`: one test per row of the classification rules API type table using `tests/fixtures/apis.json`, plus: GraphQL disabled with a mode set is REST_CLASSIC (FR-002b), MCP that is also OAS is MCP not REST_OAS, Federation with `proxyOnly` is FEDERATION, `protocol: tls` is TCP with `tls_enabled` true and `protocol: tcp` has it false (FR-002a), unknown `protocol` is NOT_UNDERSTOOD, wrong field types do not raise
- [X] T011 [P] [US1] Create `tests/unit/test_classify_auth.py`: each flag maps to its method; several flags yield a set of several methods; no flag yields NOT_SET; non-boolean flag yields NOT_UNDERSTOOD with reason `auth`; OAS definition gives the same method as an equivalent classic definition (FR-003a); OAS `securitySchemes` contradicting the flags adds NOT_UNDERSTOOD with reason `auth_oas_mismatch`
- [X] T012 [P] [US1] Create `tests/unit/test_classify_org_active.py`: organization MATCHED with name; `org_id` absent or empty gives label `Not set` and NOT_SET; unknown id gives label `<org_id> (unmatched)` and reason `org_unmatched`; organization `_id` as `ObjectId` matches a string `org_id`; `active` True/False/missing/non-boolean map to ACTIVE/INACTIVE/UNKNOWN/UNKNOWN
- [X] T013 [P] [US1] Create `tests/unit/test_snapshot_counts.py`: `build_snapshot(InMemorySource)` includes inactive APIs (FR-001), API type, organization and active counts each sum to the total (SC-006), authentication counts may exceed the total, every record is counted exactly once per non-auth dimension, and `coverage` counts unclassified APIs with reasons

### Implementation for User Story 1

- [X] T014 [US1] In `src/tyk_analyzer/classify.py` implement `classify_api_type(doc) -> tuple[ApiType, bool]` (type and `tls_enabled`) applying the classification rules API type table in the exact order given (first match wins); never raise on malformed input
- [X] T015 [US1] In `src/tyk_analyzer/classify.py` implement `classify_auth(doc) -> tuple[frozenset[AuthMethod], list[str]]` from the top-level flags table, including CUSTOM_PLUGIN and EXTERNAL_OAUTH, NOT_SET, NOT_UNDERSTOOD handling and the OAS `server.authentication.enabled` cross-check with reason `auth_oas_mismatch` (depends on T014, same file)
- [X] T016 [US1] In `src/tyk_analyzer/classify.py` implement `classify_org(doc, organizations)`, `classify_active(doc)` and `classify_api(doc, organizations) -> ApiRecord` which coerces `_id`, `api_id`, `name` and `org_id` to strings (`name` empty if absent), collects `unclassified` reasons (`api_type`, `auth`, `auth_oas_mismatch`, `org_unmatched`) and fills `evidence` with the raw values used for each classification (for example `is_oas`, `protocol`, `graphql.enabled`, each auth flag that was true, `org_id`) and never the full document (depends on T014, T015)
- [X] T017 [US1] Create `src/tyk_analyzer/snapshot.py` with `build_snapshot(source: ApiSource, now=None) -> Snapshot`: fetch organizations (id = `str(_id)`, name = `owner_name`, falling back to `owner_slug`, then id), fetch APIs, classify each, compute `Coverage`, and set `loaded_at` to the current UTC time (depends on T016)
- [X] T018 [US1] Create `src/tyk_analyzer/filters.py` with `DIMENSIONS` (`api_type`, `auth`, `org`, `active`) and `counts(records, dimension) -> list[tuple[str, int]]` sorted by count descending; authentication counts an API once per method; labels are human-readable (for example `REST (OpenAPI)`, `Universal Data Graph`, `Not understood`)
- [X] T019 [P] [US1] Create `src/tyk_analyzer/charts.py` with `breakdown_figure(title, counts, selected=())` returning a horizontal Plotly bar chart; keep category text as customdata so click events can map back to labels; highlight selected bars; height scales with the number of categories
- [X] T020 [US1] Create `src/tyk_analyzer/app.py` Streamlit entry point: page config, header, load settings, build the snapshot into `st.session_state` on first run, summary row (total, active, inactive), and four charts (API type, Authentication with the note "An API can use several methods, so counts may exceed the total.", Organization, Active state) using `counts` and `breakdown_figure`; keep all logic in the pure modules (depends on T017, T018, T019)

**Checkpoint**: US1 is fully functional. The overview matches the quickstart numbers for the local database.

---

## Phase 4: User Story 2 - Drill down from a category to the matching APIs (Priority: P1)

**Goal**: Select categories in any breakdown to filter, combine selections with AND, and inspect the matching APIs with the evidence behind each classification.

**Independent Test**: Select a category and verify the listed APIs equal the displayed count; add a second dimension and verify the intersection and that all charts update.

### Tests for User Story 2 ⚠️

- [X] T021 [P] [US2] Create `tests/unit/test_filters.py`: values within a dimension are OR, dimensions AND (FR-006a); empty selection returns all; the count of a category equals the number of records returned when that category is selected, given other active selections (FR-007); a dimension's own selection is ignored when computing its own chart counts; a combination matching nothing returns an empty list

### Implementation for User Story 2

- [X] T022 [US2] In `src/tyk_analyzer/filters.py` add `apply_selection(records, selection) -> list[ApiRecord]` (OR within a dimension, AND across) and `counts_with_selection(records, selection, dimension)` which applies every selection except the dimension's own (depends on T018)
- [X] T023 [US2] In `src/tyk_analyzer/app.py` render each chart with `st.plotly_chart(..., on_select="rerun", key=...)`, map selected points back to category labels and store them in `st.session_state.selection[dimension]`; recompute every chart from `counts_with_selection` and the totals from `apply_selection` (depends on T020, T022)
- [X] T024 [US2] In `src/tyk_analyzer/app.py` render active-selection chips with a "Clear all" button and per-chip removal (FR-009), hidden when there are no selections (no TLS filter, FR-002a)
- [X] T025 [US2] In `src/tyk_analyzer/app.py` render the matching-APIs table (name, API type, active state, authentication, organization, TLS) with "Showing N of M" and row selection (depends on T023)
- [X] T026 [US2] In `src/tyk_analyzer/app.py` render the detail panel for the selected row showing `ApiRecord.evidence` and the classification results only, never the raw stored document (FR-008)

**Checkpoint**: US1 and US2 both work. Drill-down numbers match the overview.

---

## Phase 5: User Story 3 - Refresh to see current data and understand coverage (Priority: P2)

**Goal**: Refresh loads current data and shows when; the dashboard states how much it could classify; failures and empty results are handled clearly.

**Independent Test**: Change the source data, refresh, and verify new numbers, a new load time and an updated coverage indicator; make the source fail and verify an error with no stale data.

### Tests for User Story 3 ⚠️

- [X] T027 [P] [US3] Create `tests/unit/test_snapshot_errors.py`: a source raising `SourceError` makes `build_snapshot` raise and return nothing; an empty source yields an empty snapshot with zero coverage; `loaded_at` is UTC and newer after a second build; coverage `by_reason` reports `org_unmatched` and `api_type` counts for the fixtures (FR-012, FR-004a, FR-002c)

### Implementation for User Story 3

- [X] T028 [US3] In `src/tyk_analyzer/app.py` add a Refresh button that rebuilds the snapshot, replaces the one in `st.session_state`, clears selections, and shows "Data loaded at <UTC time>" in the header (FR-010); do not use `st.cache_data` or any TTL
- [X] T029 [US3] In `src/tyk_analyzer/app.py` catch `SourceError` and `ConfigError` when loading, delete any previous snapshot from `st.session_state`, and show an error banner with the redacted reason and a Retry (Refresh) control, rendering no charts (FR-013, FR-016)
- [X] T030 [US3] In `src/tyk_analyzer/app.py` add the empty state "No Tyk API definitions found in the configured source." (FR-014) and the no-match state "No matching APIs" with Clear all, plus a loading spinner during fetch
- [X] T031 [US3] In `src/tyk_analyzer/app.py` add the coverage indicator "N of M APIs have unclassified settings" with a popover listing `Coverage.by_reason`, highlighted when N is greater than zero (FR-012)

**Checkpoint**: All three user stories work independently.

---

## Phase 7: User Story 1 and 2 extension - Optional middleware breakdowns (FR-003b)

**Goal**: Two multi-value charts, "Global middleware" and "Per-endpoint middleware", that count each API once per enabled middleware, treat classic and OpenAPI definitions the same, and filter the table like the other charts.

**Independent Test**: Run the quickstart middleware rows against the local database; the counts match, and selecting a bar lists exactly that many APIs.

### Tests for the middleware breakdowns ⚠️

- [X] T038 [P] [US1] Add fixture documents (in the separate `tests/fixtures/middleware.json`, so existing count tests are unaffected) for contracts/classification-rules.md "Optional middleware": one classic API and one OpenAPI API per row of both tables (a few documents may cover many rows), plus: a classic list entry with `"disabled": true`, an empty-but-present object (`cache_options` with `enable_cache` false, `custom_middleware` with empty values), wrong types (a string where a list is expected), an unrecognised key under `extended_paths` and `operations`, and one API with several middleware. Do not change the existing fixtures' names, because other tests look them up by name
- [X] T039 [P] [US1] Create `tests/unit/test_classify_middleware.py`: `classify_middleware(doc) -> tuple[frozenset[str], frozenset[str]]` returns the exact display names from the tables for each fixture; a `disabled: true` entry does not count; an empty-but-present object does not count; wrong types do not raise and do not count; classic and OpenAPI definitions of the same middleware give the same name; an API with no middleware returns two empty sets
- [X] T040 [P] [US2] Extend `tests/unit/test_filters.py` and `tests/unit/test_snapshot_counts.py`: `counts(records, "mw_global")` and `counts(records, "mw_endpoint")` count an API once per name and sum to more than the total when an API has several; selecting a middleware bar returns exactly the counted APIs (FR-007); an API with no middleware appears in neither chart; selections in `mw_global` and `mw_endpoint` AND-combine with the other dimensions. The "count equals rows listed" loop in `test_filters.py` must include both new dimensions

### Implementation for the middleware breakdowns

- [X] T041 [US1] In `src/tyk_analyzer/model.py` add `mw_global: frozenset[str] = frozenset()` and `mw_endpoint: frozenset[str] = frozenset()` to `ApiRecord`, placed after `auth_methods` with defaults so existing constructors keep working (data-model.md)
- [X] T042 [US1] In `src/tyk_analyzer/source.py` extend `API_PROJECTION` per contracts/source-access.md: `cache_options`, `CORS`, `global_rate_limit`, `enable_context_vars`, `enable_ip_whitelisting`, `enable_ip_blacklisting`, `enable_batch_request_support`, `enable_detailed_recording`, `do_not_track`, `event_handlers.events`, `uptime_tests.check_list`, `proxy.strip_listen_path`, `domain`, `version_data.versions`, `oas_doc.x-tyk-api-gateway.middleware`, `oas_doc.x-tyk-api-gateway.server`, `oas_doc.x-tyk-api-gateway.upstream.rateLimit`. Never project `oas_doc.paths`. Update the existing projection unit test if it asserts the exact field list
- [X] T043 [US1] In `src/tyk_analyzer/classify.py` implement `classify_middleware(doc)` applying both tables in contracts/classification-rules.md ("Enabled means" rule: non-empty list with an entry that is not `disabled: true`; `true` flags; OAS `enabled: true`; OAS operation entries present and not `enabled: false`). Iterate every version under `version_data.versions` and every operation under `middleware.operations`. Never raise on malformed input. Do not keep virtual-endpoint function bodies or any other document content in the result (research.md R11). Call it from `classify_api` and set `mw_global` and `mw_endpoint`. Depends on T041
- [X] T044 [US1] In `src/tyk_analyzer/classify.py` add the middleware names to `_evidence` (`"global middleware"` and `"per-endpoint middleware"`, comma-separated names or `(none)`) so the detail panel shows why an API was counted (FR-008)
- [X] T045 [US2] In `src/tyk_analyzer/filters.py` add `mw_global` and `mw_endpoint` to `DIMENSIONS` and `TITLES` ("Global middleware", "Per-endpoint middleware"), return `sorted(record.mw_global)` / `sorted(record.mw_endpoint)` from `labels`. Depends on T041
- [X] T046 [US1] In `src/tyk_analyzer/app.py` add both dimensions to `CHART_DIMS`, show the note "An API can use several middleware, so counts may exceed the total." under each, and add the two columns "Global middleware" and "Per-endpoint middleware" to the matching-APIs table only if the table stays readable (otherwise leave them to the detail panel). If either chart has more than 15 bars, show the top 15 plus a selector, as for organizations. Depends on T045
- [X] T047 Update `specs/001-tyk-overview-dashboard/quickstart.md` expectations with the real numbers from the local database after T043, run the full test suite and `ruff check`, and record any difference from the drafted counts. Mark T037's middleware rows verified or not

**Checkpoint**: both middleware charts show on the dashboard and match the quickstart.

---

## Phase 8: Pie charts for single-value breakdowns (FR-006c)

**Goal**: API type, Active state and Organization render as pies; Authentication and the two middleware charts stay bars. Selection, counts and filtering behave exactly as before.

- [X] T048 [P] Add `tests/unit/test_charts.py`: `pie_figure(title, rows, selected)` returns a Plotly figure with one `Pie` trace whose labels and values equal the rows, and the selected labels are pulled out; `group_top(rows, n, keep)` returns the top `n` rows plus one `("Other", sum)` row, never groups a label listed in `keep`, adds no "Other" row when there are `n` or fewer rows, and its total equals the input total
- [X] T049 Implement `pie_figure` and `group_top` in `src/tyk_analyzer/charts.py` next to `breakdown_figure` (keep `breakdown_figure` for the bar charts). Slices are labelled with the count, not a percentage; the hover text reads "<label>: <n> APIs"
- [X] T050 In `src/tyk_analyzer/app.py` render `api_type`, `active` and `org` with `pie_figure` and the other three with `breakdown_figure` (keep the same `st.plotly_chart(..., on_select="rerun", selection_mode="points")` call and key). For `org` show the top 8 plus "Other" via `group_top` with `keep` set to the selected organizations, replace `TOP_ORGS = 15` with 8 and update the selector text, and ignore a click on the "Other" slice in `_chart_selection`. Verify with Streamlit `AppTest` that the page renders without exceptions and note in the PR whether a pie click selects in the installed Streamlit version
- [X] T051 Run the full tests and `ruff check src tests`, and update `specs/001-tyk-overview-dashboard/quickstart.md` if the Organization row needs correcting

**Checkpoint**: three pies and three bar charts, filtering unchanged.

---

## Phase 9: Page layout (FR-006d)

**Goal**: Organization multiselect directly under the summary, selection chips below it, then two aligned rows of three equal-height charts, then the table.

- [X] T052 [P] Extend `tests/unit/test_charts.py`: `pie_figure` and `breakdown_figure` accept a fixed `height` and return a figure with exactly that height; pie legend sits below the plot so three pies in a row have equal plot width
- [X] T053 In `src/tyk_analyzer/charts.py` add an optional `height: int | None = None` argument to `pie_figure` and `breakdown_figure` (default keeps today's computed height) and move the pie legend below the plot (`orientation="h"`)
- [X] T054 In `src/tyk_analyzer/app.py` move the organization multiselect out of `_charts` into a new `_org_filter(records)` rendered right after `_summary` and before `_chips`, listing every organization with its count (for example "Acme (120)") and keeping the existing `orgpick` widget key so selection logic is unchanged; remove the "Find another" selector and its text. Selecting an organization in the multiselect or on the pie yields the same `org` selection (FR-006d)
- [X] T055 In `src/tyk_analyzer/app.py` lay the charts out as two `st.columns(3)` rows (pies: `api_type`, `active`, `org`; bars: `auth`, `mw_global`, `mw_endpoint`) with one fixed height per row (pies 340, bars sized to the longest of the three, capped at 520 with the chart scrolling inside its container if taller), keeping the multi-value captions under the bar row
- [X] T056 Run the full tests and `ruff check src tests`, use Streamlit `AppTest` to confirm no exceptions, a selection via the multiselect filters the table, and the chip appears; update `quickstart.md` to say the organization filter is a dropdown at the top

**Checkpoint**: layout matches contracts/ui-behavior.md.

---

## Phase 10: Remove the Organization pie, Authentication as a pie (FR-006c, FR-006d)

- [X] T057 [P] Update `tests/unit/test_charts.py`: remove the `group_top` tests only if `group_top` and the `OTHER` constant are deleted by T058; keep the `pie_figure` tests
- [X] T058 In `src/tyk_analyzer/app.py` set `PIE_DIMS = ("api_type", "active", "auth")` and `BAR_DIMS = ("mw_global", "mw_endpoint")`, delete the organization chart code (`group_top` use, `TOP_ORGS`, the `OTHER` filter in `_chart_selection`), lay out row 1 as `st.columns(3)` of pies at `PIE_HEIGHT` and row 2 as `st.columns(2)` of bars at `BAR_ROW_HEIGHT`, and keep the "counts may exceed the total" captions for `auth` and both middleware charts. `org` stays a selection dimension fed only by the multiselect, so remove `org` from `CHART_DIMS` chart-selection reading but keep `_org_filter` and the `orgpick` key. In `src/tyk_analyzer/charts.py` delete `group_top` and `OTHER` if nothing uses them. Depends on T057
- [X] T059 Run the full tests and `ruff check src tests`, use Streamlit `AppTest` to confirm no exceptions, three pies and two bar charts, and that choosing an organization filters the table; update `README.md` if it describes the charts

**Checkpoint**: layout matches contracts/ui-behavior.md.

---

## Phase 11: Compact sticky top bar (FR-006e)

- [X] T060 In `src/tyk_analyzer/app.py` build the top bar as `with st.container(key="topbar")` holding one `st.columns` row (small title as `st.markdown` with a heading size no larger than `###`, Refresh with the load time as a caption, the organization multiselect with `label_visibility="collapsed"`, and a `Clear all` button disabled when there is no selection), followed inside the same container by the chips line only when a selection exists. Remove the old `_header` layout, the separate `_org_filter` row and the separate `_chips` row; keep the `orgpick` widget key and the epoch-based clear logic
- [X] T061 In `src/tyk_analyzer/app.py` inject one `st.markdown(..., unsafe_allow_html=True)` style block (the only HTML in the app, static text) that pins `.st-key-topbar` with `position: sticky; top: 0; z-index: 999;` and a background taken from `var(--background-color)` with a bottom border, reduces `.block-container` top padding so the bar does not leave a gap, and keeps the bar one row at wide widths. Render the summary as a single `st.caption` line (total, active, inactive, unclassified with the popover kept) below the bar
- [X] T062 Run the full tests and `ruff check src tests`; use Streamlit `AppTest` to confirm no exceptions, that the bar container exists, that choosing an organization adds a chip inside it and that Clear all removes it. Check in a browser that the bar stays pinned while scrolling and does not hide the first chart at the top, and update `quickstart.md` with that check

**Checkpoint**: layout matches contracts/ui-behavior.md.

---

## Phase 12: Top bar visual fixes and browser tests (FR-006e)

- [X] T063 Fix the sticky bar found broken in a real browser: pin the layout wrapper (`[data-testid="stLayoutWrapper"]`), use the theme background from `st.context.theme.type`, one aligned row with the load time under the title
- [X] T064 Add `tests/ui/test_topbar.py` (Playwright, opt-in via `UI_URL`): one row, theme background, stays pinned, does not cover the first chart, organization choice adds and clears a chip, in dark and light themes

---

## Phase 13: Pie labels and chip filters (FR-006c)

- [X] T065 Pie slices show the category name; counts move to wrapping "Name · count" chips (`st.pills`, multi-select) under each pie, which also filter (selection key `_widget_key(dim, "pill")`); the Plotly legend is off
- [X] T066 Extend `tests/ui/test_topbar.py`: slices carry names, chips carry counts, clicking a chip adds an "API type: <name>" chip, no chip row is clipped

---

## Phase 14: Better filtering (FR-006f, FR-006g)

**Goal**: Chips and bars toggle; selected categories stand out and the rest are dimmed in every chart. Pie slices stay non-clickable by decision (a custom clickable SVG pie was built and then dropped at the user's request).

- [X] T067 Dropped: SVG pie helpers (built, tested and removed)
- [X] T068 Dropped: custom Streamlit component for a clickable pie (removed)
- [X] T069 Chips under each pie stay the pie's filter, toggling on click (`st.pills`, multi-select)
- [X] T070 Dim unselected bars and unselected pie slices (35% opacity) while a chart has a selection; tests in `tests/unit/test_charts.py`
- [X] T071 Browser tests in `tests/ui/test_topbar.py`: chip toggles on and off, unselected slices and bars dimmed, no dimming without a selection, in dark and light themes

**Checkpoint**: click a chip, see the slice highlighted and the table filter; click again, it clears.

---

## Phase 15: Remove active state (user request)

- [X] T072 Remove active state everywhere: `ActiveState`, `classify_active`, `ApiRecord.active`, the `active` projection field and filter dimension, the Active state pie, active/inactive summary counts, the Active table column and detail line; update tests; two pies now fill row 1
- [X] T073 Update spec (FR-001, FR-001a removed, FR-006a, FR-006c, FR-006d), data model, contracts, research, quickstart and README to match

---

## Phase 16: Bar filtering and fixed charts (FR-006f, FR-006h)

- [X] T074 Make charts fixed: `fixedrange` on both axes, `STATIC_CHART_CONFIG` (no mode bar, scroll zoom, double click or axis handles) on every chart; unit and browser tests that a drag and a wheel do not move the bars
- [X] T076 Found with real mouse clicks (earlier tests used synthetic clicks that hid it): a per-bar `marker.opacity` array stops Plotly reporting bar clicks, so bar dimming now uses the colour's alpha; UI tests use real mouse clicks at the bar centre
- [X] T075 Bar clicks toggle: `toggle()` in `filters.py`, an `on_select` callback that toggles the clicked category in `st.session_state` and remounts the chart (click counter in the chart key) so clicks add and remove without Shift; browser test for add, combine and remove

---

## Phase 17: Chart dropdowns in the top bar (FR-006i)

- [X] T077 Dropped (not needed): the unfiltered `counts()` already lists every category with its count, so no new helper. Originally: extend `tests/unit/test_filters.py`: `options_with_counts(records, selection, dimension)` returns every category of the dimension (unfiltered by its own selection) with its count, including categories currently selected, sorted by count descending; for the middleware dimensions an API counts once per name
- [X] T078 Dropped (see T077). Originally: implement `options_with_counts` in `src/tyk_analyzer/filters.py` . Depends on T077
- [X] T079 In `src/tyk_analyzer/app.py` rebuild `_topbar` as two rows: row 1 `st.columns` with title (and load time), Refresh, Clear all; row 2 `st.columns(5)` of `st.multiselect` dropdowns (collapsed labels, placeholder "All <dimension>", options "<name> (<count>)") for `org`, `api_type`, `auth`, `mw_global`, `mw_endpoint`; chips stay on a third line only when a selection exists. Depends on T078
- [X] T080 Share state: each dimension's dropdown, its chart and the pie chips read and write ONE session key per dimension (`_widget_key(dim, "pill")` for pies and `"bars"` for bars; reuse the same key for the dropdown, `"orgpick"` for organization) so a change in any of them updates the others; the existing epoch mechanism clears all of them. Depends on T079
- [X] T081 Extend `tests/ui/test_topbar.py`: five dropdowns render in one row of equal width under row 1; the bar stays pinned and does not cover the first chart; choosing a value in the API type dropdown highlights it in the pie, adds a chip and filters the table; clicking a bar shows the same value selected in its dropdown; Clear all empties every dropdown; run in dark and light and check screenshots before committing

**Checkpoint**: every filter is reachable from the pinned bar and stays in sync with its chart.

---

## Phase 18: Interactive dropdown counts, no chip line (FR-006j)

- [X] T082 [P] Add to `tests/unit/test_filters.py`: `dropdown_options(records, selection, dimension)` returns every category of the dimension in a fixed order (count over all `records` descending, then name, unchanged by the selection) with the count recalculated from the other dimensions' selections (own selection ignored), and `0` for categories with no matches; a selected category with no matches stays listed with 0; the count of a category equals the length of `apply_selection(records, {**other, dimension: {label}})`
- [X] T083 Implement `dropdown_options` in `src/tyk_analyzer/filters.py` (order from `counts(records, dimension)`, counts from `counts_with_selection`). Depends on T082
- [X] T084 In `src/tyk_analyzer/app.py` remove the chip line from `_topbar` (and the `chip_*` buttons), compute dropdown options with `dropdown_options(records, selection, dim)` using the current selection, show labels as "<name> (<count>)" including "(0)", and keep one row of five equal dropdowns under row 1. Depends on T083
- [X] T085 Extend `tests/ui/test_topbar.py`: no `✕` chip buttons anywhere in the bar; the bar is two rows tall; choosing "TCP" in API type changes the counts shown in the other four dropdowns and leaves the API type list order unchanged; categories with no matches show "(0)" and stay listed; Clear all restores the original counts. Update the existing browser tests that waited for a chip (use the dropdown tags and the table count instead). Check screenshots in dark and light before committing

**Checkpoint**: choosing anything in one filter updates the counts in all the others.

---

## Phase 19: Table and detail side by side (FR-006k)

- [X] T086 In `src/tyk_analyzer/app.py` split `_table` into the table and a new `_detail(rec)` and lay them out with `left, right = st.columns([2, 1])`: table left, detail right. Move the existing detail content (name and ID, API type, organization, unclassified reasons, evidence table) into `_detail` unchanged, and show `st.info("Select an API in the table to see its details.")` when no row is selected. Keep the "Showing N of M" caption and the "No matching APIs" state above or inside the left column. Reduce the table height so the two columns line up
- [X] T087 Keep the detail panel in view while the table scrolls: add a keyed container (`st.container(key="detail")`) and a CSS rule in `_STICKY_CSS` that makes its layout wrapper `position: sticky` below the sticky top bar (`top` equal to the bar's bottom edge, for example `calc(3.75rem + 7.5rem)`), with a theme background and `max-height` with `overflow-y: auto`; the panel MAY stack below the table under 900 px using a media query
- [X] T088 Add `tests/ui/test_detail_panel.py` (or extend `test_topbar.py`): the table and the panel are side by side (panel's left edge to the right of the table's right edge, same top within a few pixels); a hint shows with no selection; selecting a table row (real click on a row) fills the panel with that API's name and its evidence table; the panel stays visible after scrolling the table down; neither the table nor the panel is covered by the sticky bar; dark and light screenshots checked before committing

**Checkpoint**: click a row on the left and its details appear on the right.

---

## Phase 20: Remove the TLS column

- [X] T089 Remove the TLS column from the matching-APIs table in `src/tyk_analyzer/app.py`; TLS stays visible per API as the `protocol` value in the detail panel's evidence (FR-002a); update spec, quickstart and ui-behavior contract

---

## Phase 21: Overview and APIs tabs, aligned boxes (FR-006l)

- [X] T090 In `src/tyk_analyzer/app.py` wrap the page body in `overview, apis = st.tabs(["Overview", "APIs"])` below the top bar and summary line: charts in the Overview tab, `_table` in the APIs tab. Remove the "Matching APIs" subheader (the tab is the heading) and move the "Showing N of M" caption above `st.columns([2, 1])` so the table and the detail container start at the same height. Keep the empty states ("No matching APIs", error banner, zero APIs) outside or above the tabs
- [X] T091 Make the table use the screen height: set `TABLE_HEIGHT` from a CSS-free approach (a fixed height that fits a 900 px window after the pinned bar, for example 600) and cap the detail panel's `max-height` to match; the sticky detail rule offset must still sit just below the pinned bar
- [X] T092 Update `tests/ui/test_topbar.py` for the tabs: charts are only looked for after the Overview tab is selected (default), the table and detail tests click the APIs tab first (`page.get_by_role("tab", name="APIs")`), plus new checks: both tabs exist and Overview is selected by default; filters chosen on Overview are still applied after switching to APIs and back (dropdown tags and "Showing N of M"); the table's top edge equals the detail panel's top edge (within 2 px); the pinned bar stays visible on both tabs; run dark and light and look at screenshots of both tabs before committing

**Checkpoint**: Overview shows the charts, APIs shows the aligned table and detail, and filters carry over.

---

## Phase 22: Calmer colours (FR-006m)

- [X] T093 Add `.streamlit/config.toml` with `[theme.light]` and `[theme.dark]` teal `primaryColor` (a plain `[theme]` section would have switched off dark mode), copy it in the `Dockerfile`, set `SELECTED` in `charts.py` to the same teal and replace the pie palette with muted blues, greens and neutrals; update the unit test for the selected bar colour
- [X] T094 Look at dark and light screenshots with selections in the filters, pies and bars and run the browser tests

---

## Phase 23: Checkbox dropdowns with Clear (FR-006n)

- [X] T095 [P] Add `tests/unit/test_dropdown_summary.py` for a pure `selection_summary(title_plural, selected)` in `src/tyk_analyzer/filters.py`: nothing selected returns "All <title>", one returns the name, several return "<n> selected" (for example "API types: 2 selected"), and a long list is shortened
- [X] T096 Implement `selection_summary` in `src/tyk_analyzer/filters.py`. Depends on T095
- [X] T097 In `src/tyk_analyzer/app.py` replace each `st.multiselect` in `_dropdown` with `st.popover(summary)` holding: a Clear button (`on_click` unticks every box for that dimension and empties the stored selection), then one `st.checkbox` per category from `dropdown_options` labelled "<name> (<count>)" in the fixed order, each checkbox's state synced from the stored selection (`_selected(dim)`) before it is drawn and written back with `on_change`. Keep all categories listed, ticked ones included; no "All" button. Remove `_PLACEHOLDERS` if unused. Depends on T096
- [X] T098 Keep the popup usable for long lists: give the checkbox list a scrollable area (`st.container(height=300)`) and keep the Clear button above it; make the popover buttons equal width in the row of five
- [X] T099 Update `tests/ui/test_topbar.py` for the new dropdowns (the opener is a button, not a combobox): five equal-width openers in one row; opening one shows a checkbox on every line and a Clear button but no All button; ticking a box selects it, updates the opener summary, the table count and the other dropdowns' counts, and the box stays visible and ticked in the list; unticking removes it; Clear empties that dropdown only; Clear all in the bar still empties everything; selecting from a pie chip or a bar click ticks the same box; dark and light screenshots of an open dropdown checked before committing

**Checkpoint**: every filter dropdown shows checkboxes and a Clear button and stays in sync with the charts.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Packaging, security checks and validation across stories

- [X] T032 [P] Create `Dockerfile` (`python:3.12-slim`, install pinned dependencies from `pyproject.toml`, copy `src/`, create and switch to a non-root user, expose 8501, command `streamlit run src/tyk_analyzer/app.py --server.address 0.0.0.0`, no connection string or secret in any layer) and `.dockerignore` excluding `.env`, `.git`, `tests/`, `specs/`
- [X] T033 [P] Create `tests/integration/test_readonly.py` marked to skip unless `MONGO_URI` is set: connect with it, `fetch_apis` and `fetch_organizations` succeed, and a direct write attempt using a separate client with the same URI is rejected by the server (run with the read-only user from quickstart.md)
- [X] T034 [P] Add logging in `src/tyk_analyzer/source.py` and `src/tyk_analyzer/snapshot.py` using the standard `logging` module: log counts and durations only, never documents, the URI or credentials (Principle VIII, FR-016); add a unit test in `tests/unit/test_logging.py` that captures logs during a failed and a successful load and asserts neither contains the URI or password
- [X] T035 [P] Create `tests/unit/test_scale.py`: generate 10,000 synthetic API documents from the fixtures, run `build_snapshot` plus all five `counts`, and assert it completes in under 5 seconds (SC-005 leaves 15 s for end-to-end including the database read)
- [X] T036 Update `README.md` with: purpose, configuration table of environment variables, how to create the read-only MongoDB user (from quickstart.md), run locally, run tests, build and run the container
- [ ] T037 (partly done: classification counts, refresh, error banner without secrets and container non-root/health verified; still open: read-only write rejection needs the read-only MongoDB account, and chart-click drill-down needs a manual browser pass) Run the `quickstart.md` validation against the local database and record in the PR notes whether each expected number matches (total 6,519; API type and authentication counts; Federation list of 1; refresh changes load time; failure and read-only checks; container runs as non-root)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup; blocks all stories
- **US1 (Phase 3)**: depends on Foundational; no dependency on other stories
- **US2 (Phase 4)**: depends on Foundational and on US1's `app.py`, `filters.py` and `charts.py` (it extends them)
- **US3 (Phase 5)**: depends on US1's `app.py` and `snapshot.py`; independent of US2 except that both edit `app.py`
- **Middleware (Phase 7)**: depends on Foundational and on US1 and US2 being in place (it extends `classify.py`, `filters.py`, `source.py` and `app.py`); T038–T040 first, then T041, T042, T043, T044, T045, T046, T047 in order. T038, T039 and T040 are in different files and can run together
- **Polish (Phase 6)**: depends on the stories being complete (T037 last, after Phase 7)

### Within Each Story

- Tests first, confirmed failing
- `classify.py` tasks run in order (T014 → T015 → T016), then `snapshot.py`, then UI
- Tasks touching the same file (`classify.py`, `filters.py`, `app.py`) are sequential

### Parallel Opportunities

- Phase 2: T004, T005, T006, T007 together; then T008, T009
- US1 tests T010–T013 together; T019 (`charts.py`) in parallel with T014–T018
- US2 and US3 tests (T021, T027) can be written while US1 is implemented
- Polish: T032, T033, T034, T035 together
- Middleware: T038, T039, T040 together; T042 in parallel with T043 and T044 once T041 is done

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together:
Task: "tests/unit/test_classify_api_type.py"
Task: "tests/unit/test_classify_auth.py"
Task: "tests/unit/test_classify_org_active.py"
Task: "tests/unit/test_snapshot_counts.py"

# In parallel with the classify.py chain:
Task: "src/tyk_analyzer/charts.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup, then Phase 2 Foundational
2. Phase 3 (US1), then **stop and validate** against the quickstart numbers
3. The overview alone already answers the common questions in the spec

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → overview (MVP)
3. US2 → drill-down and cross-filtering (the constitution's traceability requirement; ship together with US1 where possible since both are P1)
4. US3 → refresh, coverage and error handling
5. Polish → container, read-only verification, quickstart sign-off

---

## Notes

- `model.py` is added to the plan's layout to hold the shared types; everything else matches plan.md.
- Commit only when explicitly asked (constitution, Development Workflow).
- Never read from production data in tests; fixtures only.
