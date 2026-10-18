# Research: Tyk Overview Dashboard

All findings come from read-only queries against the local Tyk MongoDB (`tyk_analytics`, 6,519
APIs, 22 organizations) and Tyk's public documentation. No NEEDS CLARIFICATION items remain.

## R1. Where the data lives

- **Decision**: Read `tyk_apis` (API definitions) and `tyk_organisations` (organizations) in the
  `tyk_analytics` database. Collection and database names are configurable.
- **Rationale**: These are the Dashboard's own collections. API documents are flat: fields such as
  `name`, `api_id`, `org_id`, `active`, `protocol`, `is_oas`, `graphql`, and the auth flags sit at
  the top level, with an `oas_doc` object for OpenAPI-based definitions.
- **Alternatives**: Tyk Dashboard REST API (rejected: constitution names MongoDB as the source and
  forbids relying on another service); Gateway API (rejected: only exposes loaded definitions).

## R2. Organization matching

- **Decision**: Match `str(tyk_organisations._id)` to `tyk_apis.org_id`. Name = `owner_name`.
- **Rationale**: `org_id` on APIs is a string; `_id` on organizations is an `ObjectId`. A direct
  `$lookup` matches 0 of 6,519 (verified), so conversion to string is required. (An earlier query suggested only 2 of 22 organizations were referenced; a later full read matched all 6,519 APIs to an organization, so the data had changed. Never assume.)
- **Alternatives**: Server-side `$lookup` with `$toString` (rejected: two plain reads and a Python
  dict join are simpler and give the same snapshot).

## R3. API type classification

Observed in the data (and consistent with Tyk docs) and decided:

| API type | Rule (first match wins, in this order) | Local count |
|---|---|---|
| MCP | `is_oas` and `oas_doc.x-tyk-api-gateway.middleware` has `mcpTools`, `mcpPrompts` or `mcpResources` | 1 |
| Streaming | `is_oas` and `oas_doc` has `x-tyk-streaming` | 0 |
| Federation | `graphql.enabled` and `graphql.supergraph.subgraphs` non-empty (or `graphql.execution_mode` of `supergraph`/`subgraph`) | 1 |
| UDG | `graphql.enabled` and `execution_mode == executionEngine` with data sources | 251 |
| GraphQL | `graphql.enabled` and otherwise (proxy-only) | 250 |
| TCP | `protocol` in (`tcp`, `tls`) | 500 |
| REST (OpenAPI) | `is_oas` | 2,000 |
| REST (classic) | not `is_oas`, `protocol` empty, GraphQL not enabled | 3,516 |
| not understood | anything else | 0 |

- **Rationale**: Order matters: the one MCP API is also `is_oas`, and the one federation API has
  `execution_mode: proxyOnly` but supergraph subgraphs. 16 classic APIs carry a GraphQL
  `execution_mode` while `graphql.enabled` is false; they are REST (classic), never GraphQL.
  Totals sum to 6,519.
- **TLS**: `protocol: tls` is not a type (spec FR-002a). It is recorded as the boolean
  `tls_enabled` on a TCP API and shown as a detail only (no filter). 250 of 500 TCP APIs.
- **Alternatives**: Using `graphql.execution_mode` alone (rejected: misclassifies the federation
  API and the 16 disabled ones).

## R4. Authentication classification

- **Decision**: Use the top-level auth flags for both definition styles; treat OAS
  `server.authentication` as a cross-check only.
- **Rationale**: Verified that all 2,001 OAS APIs carry top-level flags that agree with their
  OAS `securitySchemes` (1,000 keyless with no schemes; 500+1 API key; 250 JWT; 250 Basic). Flags
  work uniformly for classic APIs, giving FR-003a with one rule set.

| Method | Flag | Local count |
|---|---|---|
| none | `use_keyless` | 3,761 |
| API key | `use_standard_auth` | 1,005 |
| JWT | `enable_jwt` | 501 |
| Basic | `use_basic_auth` | 500 |
| OAuth 2.0 | `use_oauth2` | 251 |
| OpenID Connect | `use_openid` | 1 |
| Mutual TLS | `use_mutual_tls_auth` | 250 |
| Request signature | `enable_signature_checking` | 250 |

- Custom plugin auth (`use_go_plugin_auth`, `enable_coprocess_auth`, `custom_plugin_auth_enabled`)
  and `external_oauth.enabled` exist in Tyk but are 0 locally; they map to a "Custom plugin" and
  "External OAuth" method so they are never silently dropped. An API with no recognised flag set
  and keyless false is "not set".
- An OAS API whose `securitySchemes` disagree with the flags is classified by flags and counted in
  coverage as "not understood" evidence.
- **Alternatives**: Parse OAS `securitySchemes` plus `components.securitySchemes` types (rejected:
  extra branching with identical results in the observed data).

## R5. Active state

- **Decision**: Use top-level `active` (6,518 true, 1 false). Missing/non-boolean = "unknown".

## R6. Fetching efficiently

- **Decision**: One `find` on `tyk_apis` with an explicit projection (identity, `active`,
  `protocol`, `is_oas`, `graphql.enabled/execution_mode/supergraph.subgraphs/engine.data_sources`
  existence-relevant paths, auth flags, `listen_port`, and the three MCP/streaming marker paths
  under `oas_doc`), plus one `find` on `tyk_organisations` (`_id`, `owner_name`). Drop heavy
  bodies (`oas_doc.paths`, `schema`) by never projecting them.
- **Rationale**: Keeps load time and memory small at 10k APIs and avoids copying sensitive config
  (constitution VIII).
- **Alternatives**: Server-side aggregation computing categories (rejected: puts business rules in
  Mongo pipelines, harder to unit test).

## R7. Read-only enforcement

- **Decision**: Defence in depth: (1) deployment docs require a MongoDB user with only the `read`
  role on the database; (2) `MongoApiSource` exposes only two read methods and never imports write
  APIs; (3) unit test asserts the class has no write-capable methods; (4) opt-in integration test
  confirms a write is rejected when connected with the read-only URI.
- **Alternatives**: Application-level promise only (rejected by Principle I).

## R8. Streamlit interaction model

- **Decision**: `st.plotly_chart(fig, on_select="rerun", key=...)` for charts (pies for single-value
  dimensions, bars for multi-value ones, FR-006c); selected slices or bars
  update `st.session_state.selection[dimension]`. Selections AND-combine; every chart's counts
  are recomputed from the filtered subset. Active chips with a "Clear" control; a data table of
  matching APIs with a detail expander.
- **Rationale**: Native cross-filtering with no custom components. Horizontal bars scale to many
  organizations (tall chart + search/limit to top N with the rest reachable through a selector).
- **Alternatives**: Selectboxes only (rejected: weaker discoverability); custom JS component
  (rejected: violates Principle VII).

## R9. Snapshot and refresh

- **Decision**: Build the snapshot into `st.session_state` on first load and on the Refresh
  button; show "Data loaded at <time>". On failure show an error and no data from earlier loads.
  No `st.cache_data`, no TTL.
- **Rationale**: Principle VI.

## R10. Packaging

- **Decision**: `python:3.12-slim`, non-root user, pinned dependencies in `pyproject.toml`,
  `streamlit run src/tyk_analyzer/app.py --server.address 0.0.0.0`. Config via `MONGO_URI`,
  `MONGO_DB`, `TYK_APIS_COLLECTION`, `TYK_ORGS_COLLECTION`, `MONGO_TIMEOUT_MS`. No compose file
  assumed (Principle IX: no assumed orchestrator).

## R11. Optional middleware (FR-003b)

- **Decision**: Two multi-value dimensions, `mw_global` and `mw_endpoint`. Classic and OpenAPI
  definitions map to one shared list of display names (contracts/classification-rules.md). A
  middleware counts only when explicitly enabled: for classic lists, at least one entry whose
  `disabled` is not true; for OAS, an object with `enabled` true (or, for operation-level entries,
  present and not `enabled: false`). Fields present on every document with empty values
  (`custom_middleware.auth_check`, `proxy` without `strip_listen_path`, `session_provider`) do not
  count.
- **Where it lives** (observed in the 6,519 local APIs): classic global settings are top-level
  fields (`cache_options`, `CORS`, `global_rate_limit`, `enable_context_vars`, ...) and
  `version_data.versions.*.global_*`; classic per-endpoint settings are lists under
  `version_data.versions.*.extended_paths`. OAS global settings are under
  `x-tyk-api-gateway.middleware.global`, per-endpoint under `middleware.operations.<id>.<name>`,
  server-level under `x-tyk-api-gateway.server`.
- **Observed counts**: Global: strip listen path 5,767; context variables 4,750; do not track
  1,750; rate limit (API) 750; event handlers 750; custom domain 750; cache 518; CORS 503; request
  and response header transform 500 each; traffic logs 251; batch requests, IP allow list, override
  target, uptime tests 250 each. Per endpoint: virtual endpoint 5,502; request header transform and
  ignore authentication 501; request size limit, track endpoint, circuit breaker, cache, validate
  request, URL rewrite, enforce timeout 500 each; allow list 253; the rest 250 each.
- **Data volume**: `version_data` is about 11 MB across all APIs and the largest single document
  fragment is 13 KB, so fetching `version_data.versions` and the OAS `middleware` and `server`
  subtrees is acceptable for SC-005. Virtual endpoint function bodies are dropped immediately
  after classification and never stored on the record. `oas_doc.paths` stays excluded.
- **Alternatives**: One chart per middleware (rejected by clarification); server-side `$project`
  aggregation to compute booleans (rejected: dict-keyed versions make it fragile, and the data
  volume does not justify it).
