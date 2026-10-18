# Contract: Source Access

## Interface

```text
ApiSource (protocol)
  fetch_apis()          -> list[dict]     # projected API documents
  fetch_organizations() -> list[dict]     # {_id, owner_name, owner_slug}
```

`snapshot.build_snapshot(source) -> Snapshot` is the only caller. Tests use an in-memory
implementation fed from `tests/fixtures`.

## MongoApiSource rules

- Reads only: `find` with an explicit projection. No other collection methods are used or
  exposed. Unit test: the class has no public method other than the two above and the module does
  not reference write operations.
- Configuration (environment): `MONGO_URI` (required, secret), `MONGO_DB` (default
  `tyk_analytics`), `TYK_APIS_COLLECTION` (default `tyk_apis`), `TYK_ORGS_COLLECTION` (default
  `tyk_organisations`), `MONGO_TIMEOUT_MS` (default 5000).
- Projection (APIs): `name`, `api_id`, `org_id`, `protocol`, `is_oas`, `listen_port`,
  the auth flags listed in classification-rules.md, `external_oauth.enabled`,
  `graphql.enabled`, `graphql.execution_mode`, `graphql.supergraph.subgraphs`,
  `graphql.engine.data_sources`, and the OAS marker paths
  `oas_doc.x-tyk-api-gateway.middleware.{mcpTools,mcpPrompts,mcpResources}`,
  `oas_doc.x-tyk-api-gateway.server.authentication.enabled`, `oas_doc.x-tyk-streaming`.
  For middleware: the global flags and objects named in classification-rules.md,
  `version_data.versions` (the `global_*`, `override_target` and `extended_paths` keys only), and
  `oas_doc.x-tyk-api-gateway.{middleware,server,upstream.rateLimit}`.
  Heavy bodies (`oas_doc.paths`, `graphql.schema`, certificates, secrets) are never fetched.
- Read must complete fully: a cursor error or timeout raises `SourceError`; partial lists are
  never returned (FR-013).
- `SourceError` messages never contain the connection string, user name or password (FR-016).

## Required database permissions

A MongoDB user with the built-in `read` role on the Tyk database only. Documented in
`quickstart.md`.
