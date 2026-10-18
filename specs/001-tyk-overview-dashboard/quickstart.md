# Quickstart: Validating the Tyk Overview Dashboard

Runnable checks that prove the feature works end to end. Rules are in
[contracts/classification-rules.md](contracts/classification-rules.md); entities in
[data-model.md](data-model.md).

## Prerequisites

- Python 3.12+ and Docker.
- A reachable MongoDB with the Tyk Dashboard database (`tyk_analytics`).
- A MongoDB user with only the `read` role on that database. Example (run once by an admin):

  ```text
  db.getSiblingDB("tyk_analytics").createUser({user: "tyk_analyzer_ro", pwd: "<secret>",
    roles: [{role: "read", db: "tyk_analytics"}]})
  ```

  The local development database has no authentication; use it for development only.

## 1. Unit tests (no database needed)

```text
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
pytest tests/unit   # or: .venv/bin/python -m pytest tests/unit
```

Expected: all pass, including one test per classification rule row and the read-only guard.

## 2. Run against the local database

```text
export MONGO_URI="mongodb://localhost:27017"
streamlit run src/tyk_analyzer/app.py
```

Expected for the local dataset (6,519 APIs):

| Check | Expected |
|---|---|
| Total | 6,519 (6,518 active, 1 inactive) |
| API type | REST classic 3,516; REST OpenAPI 2,000; GraphQL 250; UDG 251; Federation 1; MCP 1; TCP 500 |
| TLS detail on TCP | 250 of 500 TCP APIs show TLS in the table; there is no TLS filter |
| Authentication | none 3,761; API key 1,005; JWT 501; Basic 500; OAuth 2.0 251; mutual TLS 250; request signature 250; OpenID Connect 1 |
| Global middleware | Strip listen path 5,767; Context variables 4,750; Do not track 1,750; Rate limit (API), Event handlers, Custom domain 750 each; Cache 518; CORS 503; header transforms 500 each; Traffic logs 251 |
| Per-endpoint middleware | Virtual endpoint 5,502; Ignore authentication 501; Request size limit, Track endpoint, Circuit breaker, Cache, Validate request, URL rewrite, Enforce timeout 500 each; Allow list 253 |
| Organization | counts sum to 6,519; the dropdown at the top lists every organization; there is no organization chart |
| Click "Federation" | exactly 1 API listed; its detail shows supergraph evidence |
| Click "JWT" then "REST (OpenAPI)" | list shrinks to the intersection; all charts update |
| Refresh | load time changes |

## 3. Failure behavior

- Stop the database (or set `MONGO_URI` to a closed port) and click Refresh: an error banner
  appears, no charts, and the message does not contain the URI.
- Using the read-only user, run the opt-in integration test:

  ```text
  MONGO_URI="mongodb://tyk_analyzer_ro:<secret>@localhost:27017/tyk_analytics" \
    pytest tests/integration
  ```

  Expected: reads succeed and a write attempt is rejected by the server.

## 4. Container

```text
docker build -t tyk-analyzer .
docker run --rm -p 8501:8501 -e MONGO_URI="$MONGO_URI" tyk-analyzer
```

Expected: dashboard at `http://localhost:8501`; `docker run ... id -u` prints a non-zero user; the
image contains no connection string (`docker history` and image files).
