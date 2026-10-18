# Tyk API Analyzer

A read-only dashboard that shows how Tyk is used across the API definitions stored in the Tyk
Dashboard's MongoDB: API type, authentication method, organization and active state, with
drill-down to the matching APIs and the evidence behind each classification.

It never writes to MongoDB. Specifications and design notes are in
`specs/001-tyk-overview-dashboard/`; project rules are in `.specify/memory/constitution.md`.

## Configuration

All settings come from environment variables (see `.env.example`). Nothing is baked into the image.

| Variable | Default | Meaning |
|---|---|---|
| `MONGO_URI` | required | MongoDB connection string (a secret) |
| `MONGO_DB` | `tyk_analytics` | Tyk Dashboard database |
| `TYK_APIS_COLLECTION` | `tyk_apis` | API definitions collection |
| `TYK_ORGS_COLLECTION` | `tyk_organisations` | Organizations collection |
| `MONGO_TIMEOUT_MS` | `5000` | Server selection timeout |

### Read-only MongoDB user

Connect with an account that has only the `read` role on the Tyk database:

```text
db.getSiblingDB("tyk_analytics").createUser({user: "tyk_analyzer_ro", pwd: "<secret>",
  roles: [{role: "read", db: "tyk_analytics"}]})
```

## Run locally

```text
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
MONGO_URI=mongodb://localhost:27017 .venv/bin/streamlit run src/tyk_analyzer/app.py
```

## Test

```text
.venv/bin/python -m pytest                 # unit tests, no database needed
MONGO_URI=... .venv/bin/python -m pytest tests/integration
```

The write-rejection check runs only with `TYK_EXPECT_READONLY=1` and the read-only account.

## Container

Dependencies are installed from `requirements.lock` (regenerate with
`uv pip compile pyproject.toml -o requirements.lock --python-version 3.12`).

```text
docker build -t tyk-analyzer .
docker run --rm -p 8501:8501 -e MONGO_URI="$MONGO_URI" tyk-analyzer
```

The container runs as a non-root user. Open http://localhost:8501.

## Browser tests

`tests/ui` drives the running dashboard with Playwright (sticky top bar, dark and light themes). It is
skipped unless `UI_URL` is set:

```bash
pip install playwright pytest && playwright install chromium
streamlit run src/tyk_analyzer/app.py &
UI_URL=http://localhost:8501 pytest tests/ui   # UI_BROWSER_CHANNEL=chrome to use installed Chrome
```
