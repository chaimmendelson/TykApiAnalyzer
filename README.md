# Tyk API Analyzer

A read-only dashboard that shows how Tyk is used across the API definitions stored in the Tyk
Dashboard's MongoDB: API type, authentication method, organization and middleware, with
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

## CI and releases

GitHub Actions (`.github/workflows`):

- **CI** (`ci.yml`) runs on every push and pull request: `ruff`, the unit tests (no MongoDB needed; the
  integration and browser tests skip themselves), and a Docker build that also checks the container runs
  as a non-root user and reports healthy.
- **Release** (`release.yml`) runs when you publish a GitHub release. It runs the same tests, then builds
  a `linux/amd64` + `linux/arm64` image and pushes `chaimmendelson/tyk-api-analyzer` to Docker Hub as
  `X.Y.Z`, `X.Y` and `latest` (a pre-release such as `v1.2.3-rc1` only gets its own tag).

One-time setup: add the Docker Hub login as repository secrets (paste the values when prompted; a token
comes from Docker Hub > Account settings > Personal access tokens, with Read & Write):

```bash
gh secret set DOCKERHUB_USERNAME -R chaimmendelson/TykApiAnalyzer
gh secret set DOCKERHUB_TOKEN -R chaimmendelson/TykApiAnalyzer
```

Cut a release (the release tag decides the image tag; the version in `pyproject.toml` is informational):

```bash
gh release create v1.0.0 --generate-notes
```
