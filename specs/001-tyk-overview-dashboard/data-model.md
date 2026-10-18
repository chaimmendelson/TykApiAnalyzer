# Data Model: Tyk Overview Dashboard

In-memory only. Nothing is persisted. Built once per refresh (the "snapshot").

## Enumerations

**ApiType**: `REST_CLASSIC`, `REST_OAS`, `GRAPHQL`, `UDG`, `FEDERATION`, `MCP`, `TCP`,
`STREAMING`, `NOT_UNDERSTOOD`. One per API (FR-002b).

**AuthMethod**: `NONE`, `API_KEY`, `JWT`, `BASIC`, `OAUTH2`, `OPENID`, `MUTUAL_TLS`,
`REQUEST_SIGNATURE`, `CUSTOM_PLUGIN`, `EXTERNAL_OAUTH`, `NOT_SET`, `NOT_UNDERSTOOD`.
An API has a non-empty set.

**ActiveState**: `ACTIVE`, `INACTIVE`, `UNKNOWN`.

## ApiRecord (one per document in the APIs collection)

| Field | Type | Source / rule |
|---|---|---|
| `id` | str | `_id` as string; unique identity |
| `api_id` | str or None | `api_id` |
| `name` | str | `name`, empty string if absent |
| `active` | ActiveState | top-level `active` |
| `api_type` | ApiType | contracts/classification-rules.md |
| `tls_enabled` | bool | `protocol == "tls"`; only meaningful for TCP |
| `auth_methods` | frozenset[AuthMethod] | contracts/classification-rules.md |
| `mw_global` | frozenset[str] | display names of enabled global middleware (contracts/classification-rules.md) |
| `mw_endpoint` | frozenset[str] | display names of enabled per-endpoint middleware |
| `org_id` | str or None | `org_id` |
| `org_label` | str | organization name, `Not set`, or `<id> (unmatched)` |
| `org_status` | `MATCHED`, `NOT_SET`, `UNMATCHED` | org resolution |
| `unclassified` | tuple[str] | reasons this API counts toward coverage (e.g. `api_type`, `auth`, `org_unmatched`, `auth_oas_mismatch`) |
| `evidence` | dict[str, str] | the raw values behind each classification, shown in the detail panel (FR-008); never the full document |

Validation: `name` and ids are coerced to strings; any field of unexpected type yields
`NOT_UNDERSTOOD` rather than an exception (spec edge case: malformed definitions).

## Organization (one per document in the organizations collection)

| Field | Type | Source |
|---|---|---|
| `id` | str | `str(_id)` |
| `name` | str | `owner_name` (falls back to `owner_slug`, then id) |

Relationship: `ApiRecord.org_id` references `Organization.id` (string comparison).

## Snapshot

| Field | Type | Notes |
|---|---|---|
| `records` | list[ApiRecord] | all APIs, including inactive (FR-001) |
| `organizations` | dict[str, Organization] | |
| `loaded_at` | datetime (UTC) | shown to user (FR-010) |
| `coverage` | Coverage | derived |

## Coverage

`total`, `unclassified_count` (APIs with a non-empty `unclassified`), and `by_reason` counts
(FR-012, FR-004a, FR-002c).

## Selection (UI state)

`dict[Dimension, set[str]]` over dimensions `api_type`, `auth`, `org`, `active`, `mw_global`, `mw_endpoint`. Within a
dimension, values OR; across dimensions, AND (FR-006a). Empty = no constraint.

## Breakdown (derived)

`counts(records, dimension) -> list[(category, count)]`. Authentication and the two middleware dimensions count a multi-valued API
once per value, so they may exceed the total; an API with no middleware is in no bar. All other dimensions sum to the total (SC-006).
When selections exist, counts are computed over the filtered subset, except that a dimension's own
selection is ignored for its own chart so users can see sibling categories.

## State transitions

Snapshot: `none → loaded` on first open; `loaded → loaded(new)` on Refresh; `* → error` on read
failure (the previous snapshot is discarded, not shown).
