# Contract: Classification Rules

`classify.py` implements these rules as pure functions over one API document (a plain dict) and
the organizations map. They are the testable core of the feature. Counts are from the local
dataset used during research.

## API type (first matching row wins)

| # | Condition | Result |
|---|---|---|
| 1 | `is_oas` is true and `oas_doc["x-tyk-api-gateway"].middleware` has key `mcpTools`, `mcpPrompts` or `mcpResources` | MCP |
| 2 | `is_oas` is true and `oas_doc` has key `x-tyk-streaming` | STREAMING |
| 3 | `graphql.enabled` is true and (`graphql.supergraph.subgraphs` non-empty, or `graphql.execution_mode` in `supergraph`, `subgraph`) | FEDERATION |
| 4 | `graphql.enabled` is true and `graphql.execution_mode == "executionEngine"` | UDG |
| 5 | `graphql.enabled` is true | GRAPHQL |
| 6 | `protocol` in `tcp`, `tls` | TCP (`tls_enabled = protocol == "tls"`) |
| 7 | `is_oas` is true | REST_OAS |
| 8 | `is_oas` is not true and `protocol` is empty or absent | REST_CLASSIC |
| 9 | otherwise (for example an unknown `protocol` value, or wrong field types) | NOT_UNDERSTOOD |

Notes: `graphql.enabled` false never yields a GraphQL type, even if `execution_mode` is set
(FR-002b). TLS is never a type (FR-002a).

## Authentication (set of methods)

Top-level flags, applied to classic and OpenAPI-based definitions alike (FR-003a):

| Flag true | Method |
|---|---|
| `use_keyless` | NONE |
| `use_standard_auth` | API_KEY |
| `enable_jwt` | JWT |
| `use_basic_auth` | BASIC |
| `use_oauth2` | OAUTH2 |
| `use_openid` | OPENID |
| `use_mutual_tls_auth` | MUTUAL_TLS |
| `enable_signature_checking` | REQUEST_SIGNATURE |
| `use_go_plugin_auth`, `enable_coprocess_auth`, `custom_plugin_auth_enabled` | CUSTOM_PLUGIN |
| `external_oauth.enabled` | EXTERNAL_OAUTH |

- If no flag is true: NOT_SET.
- If a flag is present but not a boolean: NOT_UNDERSTOOD (plus unclassified reason `auth`).
- For OpenAPI-based definitions, if `server.authentication.enabled` is true while no auth flag is
  true, or the flags say keyless while schemes are enabled, add NOT_UNDERSTOOD and reason
  `auth_oas_mismatch`.

## Organization

| Condition | `org_label` | `org_status` |
|---|---|---|
| `org_id` absent or empty | `Not set` | NOT_SET |
| `org_id` equals an organization `id` | organization name | MATCHED |
| otherwise | `<org_id> (unmatched)` | UNMATCHED (reason `org_unmatched`) |

## Active state

`active is True` → ACTIVE, `False` → INACTIVE, anything else → UNKNOWN.

## Coverage

An API is unclassified when its type is NOT_UNDERSTOOD, its auth set contains NOT_UNDERSTOOD, or
its organization is UNMATCHED. The indicator reports the count and the reasons.

## Test obligations

One fixture per row above, plus: GraphQL disabled with a mode set; MCP that is also OAS;
federation with `proxyOnly`; non-boolean flags; missing fields; ObjectId vs string organization
identifiers; an API with several auth flags.

## Optional middleware (FR-003b)

Each API gets two sets of display names, `mw_global` and `mw_endpoint`. A name is in a set when
the setting is explicitly enabled (see below); an API counts once per name.

**Enabled means**: classic list entries: the list is non-empty and has an entry without
`disabled: true`; classic boolean flags: `true`; classic objects: the flag named below; OAS
objects: `enabled: true`; OAS operation entries: present and not `enabled: false`. Anything of an
unexpected type is not enabled and never raises.

### Global middleware

| Display name | Classic | OpenAPI |
|---|---|---|
| Cache | `cache_options.enable_cache` | `middleware.global.cache` |
| CORS | `CORS.enable` | `middleware.global.cors` |
| Rate limit (API) | `global_rate_limit.rate` > 0 | `upstream.rateLimit` |
| Context variables | `enable_context_vars` | `middleware.global.contextVariables` |
| Request header transform | `versions.*.global_headers` non-empty | `middleware.global.transformRequestHeaders` |
| Response header transform | `versions.*.global_response_headers` non-empty | `middleware.global.transformResponseHeaders` |
| IP allow list / IP block list | `enable_ip_whitelisting` / `enable_ip_blacklisting` | n/a |
| Batch requests | `enable_batch_request_support` | n/a |
| Traffic logs | `enable_detailed_recording` | `middleware.global.trafficLogs`, `server.detailedActivityLogs` |
| Do not track | `do_not_track` | n/a |
| Event handlers | `event_handlers.events` non-empty | `server.eventHandlers` |
| Uptime tests | `uptime_tests.check_list` non-empty | n/a |
| Strip listen path | `proxy.strip_listen_path` | `server.listenPath.strip` |
| Override target | `versions.*.override_target` non-empty | n/a |
| Custom domain | `domain` non-empty | `server.customDomain` |

### Per-endpoint middleware

| Display name | Classic `extended_paths.*` | OpenAPI `operations.*` |
|---|---|---|
| Allow list / Block list | `white_list` / `black_list` | `allow` / `block` |
| Ignore authentication | `ignored` | `ignoreAuthentication` |
| Cache | `cache`, `advance_cache_config` | `cache` |
| Circuit breaker | `circuit_breakers` | `circuitBreaker` |
| Enforce timeout | `hard_timeouts` | `enforceTimeout` |
| Rate limit | `rate_limit` | `rateLimit` |
| Request size limit | `size_limits` | `requestSizeLimit` |
| URL rewrite | `url_rewrites` | `urlRewrite` |
| Validate request | `validate_json` | `validateRequest` |
| Mock response | n/a | `mockResponse` |
| Virtual endpoint | `virtual` | `virtualEndpoint` |
| Method transform | `method_transforms` | n/a |
| Body transform | `transform`, `transform_response` | `transformRequestBody`, `transformResponseBody` |
| Request / Response header transform | `transform_headers` / `transform_response_headers` | `transformRequestHeaders` / `transformResponseHeaders` |
| Track endpoint / Do not track endpoint | `track_endpoints` / `do_not_track_endpoints` | `trackEndpoint` / `doNotTrackEndpoint` |
| Internal endpoint | `internal` | `internal` |

An unrecognised key under these locations is ignored (not a coverage issue). Middleware has no
"not set" bar: an API with none simply does not appear in the middleware charts.

Test obligations: one fixture per row for both styles, a `disabled: true` entry that must not
count, an empty-but-present object that must not count, wrong types, and an API with several
middleware counting once per name.
