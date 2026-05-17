# Dataset Discovery Platform

A seeded local dataset discovery demo that combines DuckDB-backed catalog storage, a FastAPI API, a background artifact worker, and a browser UI for searching datasets and previewing schema metadata.

## Tech Stack Snapshot

- **Backend / API:** Python 3.12, FastAPI, Uvicorn, Pydantic
- **Data / Storage:** DuckDB
- **External integration:** Hugging Face Hub, `httpx`, `tenacity`
- **UI / Demo:** static HTML, CSS, JavaScript, `http.server`
- **Engineering:** pytest, GitHub Actions

## Why This Project Exists

Dataset discovery is more than listing records in a table. Useful discovery flows need searchable metadata, schema visibility, policy checks, artifact retrieval, and enough operational structure to make the system testable and repeatable.

This repository packages those concerns into a compact public demo. Instead of a notebook-only prototype, it shows a small but realistic application boundary:

- a local analytical store for dataset metadata
- an HTTP API for search and artifact access
- a background worker for on-demand resolution
- a browser UI for search, filtering, metrics, and schema preview

The supported scope is intentionally narrow: this repo is a reproducible local seeded demo, not a claim of production deployment or live customer usage.

## What This Project Builds

This project builds:

- a seeded dataset catalog stored in DuckDB
- a versioned `/v2` FastAPI service for search, policy checks, artifact retrieval, and admin operations
- a lightweight worker that resolves schema/sample artifacts asynchronously
- a static browser UI for discovery, filtering, metrics, and schema preview
- reproducible setup scripts, smoke tests, and CI for the supported local demo path

The repo also contains an optional Hugging Face-backed discovery path in code, but that path is not required for the public demo and is not the primary validated workflow described here.

## Architecture / Workflow

```text
tests/fixtures/demo_catalog.json
  -> scripts/create_demo_db.py
  -> DuckDB catalog + seeded artifacts
  -> FastAPI app (/v2/*)
  -> background worker for artifact resolution
  -> static UI (src/ui/index.html)
```

### Component Map

| Component | Role | Evidence |
|---|---|---|
| Seed fixture | Provides reproducible demo datasets and one cached schema artifact | `tests/fixtures/demo_catalog.json` |
| Demo DB builder | Creates the local DuckDB file from the fixture | `scripts/create_demo_db.py`, `scripts/demo_data.py` |
| Storage layer | Stores datasets, artifacts, jobs, events, signals, connector state, and search content | `src/storage/duckdb_backend.py` |
| API layer | Exposes search, resolve, artifact, policy, metrics, and admin endpoints | `src/api/routes.py`, `src/api/main.py` |
| Worker | Claims queued jobs and writes resolved artifacts back to storage | `src/api/worker.py` |
| Connectors | Fetches schema/sample data from Hugging Face or an offline stub | `src/connectors/` |
| UI | Renders search, filters, metrics, pagination, and schema preview | `src/ui/index.html` |
| Verification | Runs smoke tests locally and in CI | `tests/test_smoke_api.py`, `.github/workflows/ci.yml` |

## Key Features

### Search and Discovery

- Searches dataset title, description, README text, tags, modalities, and languages.
- Supports metadata filters for license, modality, language, and size class.
- Returns lightweight reasoning signals for why a query matched.

### Artifact Resolution

- Fetches cached schema artifacts when already available.
- Queues new schema/sample resolution jobs when artifacts are missing.
- Applies policy checks before queueing work.

### Operations and Observability

- Exposes health and admin endpoints under `/v2/*`.
- Tracks freshness, thin-README coverage, queue depth, schema coverage, and job error taxonomy.
- Includes bounded admin operations for index rebuilds, discovery runs, and prefetch.

### Reproducibility

- Builds the demo catalog from a committed fixture.
- Includes repo-root scripts for database creation, API startup, UI serving, and smoke tests.
- Runs the same supported path in GitHub Actions CI.

## Technical Implementation

### Core Components

- **Storage adapter:** `DuckDBStorage` initializes tables for datasets, artifacts, jobs, events, signals, connector cursors, dataset state, and search documents.
- **Search layer:** the storage adapter builds a `dataset_search` table and prefers DuckDB FTS when available, with a LIKE-based fallback when FTS is unavailable or returns no hits.
- **API layer:** the FastAPI app registers `/v2/healthz`, `/v2/search_index`, `/v2/request_resolve`, `/v2/get_artifact`, `/v2/policy_check`, `/v2/log_signal`, and admin routes.
- **Worker loop:** the background worker reclaims stale jobs, claims queued jobs, calls a connector, writes artifacts, and records success or error events.
- **Policy layer:** resolution is gated by public access, license allowlist, optional size ceilings, and request budget limits.
- **UI layer:** the browser app issues API calls directly, renders cards for datasets, exposes filters and metrics, and lets users resolve or inspect schemas.

### Important Implementation Details

- Search state is rebuilt from dataset content rather than stored as a separate external service.
- Artifact staleness is tied to dataset fingerprint changes.
- The worker classifies common failures such as timeout, rate limiting, network errors, and parse errors.
- DuckDB is the only supported storage backend in the validated local demo path; any non-DuckDB storage code should be treated as experimental or future-facing unless separately documented.

### Outputs and Artifacts

- local DuckDB demo file under `data/`
- cached schema artifacts in the DuckDB store
- admin metrics from `/v2/admin`
- seeded UI screenshots under `assets/screenshots/`

## Data / Inputs / Assumptions

- The supported demo data is a small committed fixture in `tests/fixtures/demo_catalog.json`.
- The fixture contains three example datasets plus one seeded schema artifact.
- The default public demo assumes local execution against a DuckDB file created from that fixture.
- The repo does not commit external raw datasets, model weights, or large benchmark artifacts.
- `HF_TOKEN` is only relevant for the optional Hugging Face-backed connector path; it is not required for the seeded local demo.
- Search and schema behavior should be interpreted as demo functionality, not as evidence of production-scale data coverage.

## Methodology / Approach

The project uses a pragmatic retrieval-and-resolution approach rather than a learned ranking stack:

- search over normalized metadata and README text
- prefer DuckDB FTS when available
- fall back to tokenized LIKE matching when FTS support is unavailable
- resolve schema/sample artifacts on demand instead of precomputing everything
- gate artifact resolution with explicit access, license, size, and budget policies
- prefetch likely-useful schema jobs for thin public datasets when runtime conditions allow it

This keeps the system reproducible in a single local repo while still showing realistic component boundaries.

## Evaluation / Results

### Verified in Repository

| Evidence | What it shows | Source |
|---|---|---|
| Smoke tests | The repo defines tests for app startup, health, search, admin metrics, artifact retrieval, and cached resolve flow | `tests/test_smoke_api.py` |
| CI workflow | GitHub Actions runs the seeded demo DB build and smoke path on Python 3.12 | `.github/workflows/ci.yml` |
| Screenshots | The UI can render seeded search results, filters, and schema preview states | `assets/screenshots/` |

### Honest Boundaries

- No offline relevance benchmark metrics are committed.
- No latency, throughput, or load-test report is committed.
- No production deployment, user adoption, or business impact evidence is claimed here.

## Demo / Screenshots / Example Outputs

### Supported Demo Queries

- `text classification`
- `fraud`
- `image`

### Screenshots

![Seeded text classification search](assets/screenshots/search_text_classification.png)

Search results over the seeded catalog.

![Seeded fraud result with schema open](assets/screenshots/dataset_detail_fraud.png)

Dataset detail state with schema preview visible.

![Seeded size-class filter state](assets/screenshots/search_filtered_size_class.png)

Filtered search state using metadata controls exposed by the UI.

## Quickstart

These commands are the supported local demo path from the repository root.

### 1. Create an environment and install dependencies

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

### 2. Build the seeded demo database

```bash
./.venv/bin/python -m scripts.create_demo_db --db-path data/demo_discovery.duckdb
```

### 3. Start the API

```bash
DUCKDB_PATH=data/demo_discovery.duckdb ./.venv/bin/python -m scripts.run_api --host 127.0.0.1 --port 8000
```

### 4. Start the UI in a second terminal

```bash
./.venv/bin/python -m scripts.serve_ui --host 127.0.0.1 --port 8080
```

### 5. Open the demo

- API health: `http://127.0.0.1:8000/v2/healthz`
- UI: `http://127.0.0.1:8080`

### 6. Run smoke tests

```bash
./scripts/run_smoke_tests.sh
```

### Optional Environment Variables

| Variable | Purpose | Needed for seeded demo? |
|---|---|---|
| `DUCKDB_PATH` | Points the API at the local DuckDB file | yes |
| `STORAGE_BACKEND` | Chooses `duckdb` or `postgres` backend | no, defaults to `duckdb` |
| `HF_TOKEN` | Auth for optional Hugging Face-backed calls | no |
| `PREFETCH_ENABLED` | Enables or disables prefetch behavior | no |

## Repository Structure

```text
dataset-discovery-platform/
├── .github/workflows/ci.yml
├── assets/screenshots/
├── data/.gitkeep
├── scripts/
│   ├── create_demo_db.py
│   ├── demo_data.py
│   ├── run_api.py
│   ├── run_smoke_tests.sh
│   └── serve_ui.py
├── src/
│   ├── api/
│   ├── config/
│   ├── connectors/
│   ├── storage/
│   ├── tools/
│   └── ui/
├── tests/
│   ├── fixtures/demo_catalog.json
│   └── test_smoke_api.py
├── README.md
└── requirements.txt
```

## Ownership / What This Repository Demonstrates

This public repository is the standalone demo implementation for the dataset discovery platform. It is intentionally scoped around the seeded local demo path and does not include private infrastructure, internal datasets, or the historical V1 pipeline repository.

The repo demonstrates:

- DuckDB-backed catalog storage and search indexing
- FastAPI routes and request/response schemas
- background job handling for artifact resolution
- policy checks and admin metrics
- static UI for search and schema preview
- demo-data creation scripts, smoke tests, and CI wiring

This project should be read as a public portfolio/demo surface, not as a claim that the seeded fixture represents the full historical dataset collection pipeline.

## Design Decisions and Tradeoffs

- **Seeded local demo instead of live ingest:** keeps the public repo reproducible without depending on private infrastructure or external availability.
- **DuckDB-first storage:** simplifies setup and makes the project easy to run locally, while still showing relational tables, search state, and job tracking.
- **Background worker instead of synchronous artifact fetch on every request:** keeps API boundaries explicit and supports cached artifact behavior.
- **Optional Hugging Face path kept behind the supported demo flow:** shows how the system can integrate with external metadata without making that path a requirement for validation.
- **Static UI instead of a heavier frontend framework:** keeps the demo lightweight and inspectable while still exposing the main interaction flow.

## Limitations / Honest Scope

- The supported path is a seeded local demo, not a full reproduction of live discovery or ingestion workflows.
- Only DuckDB is implemented for the validated demo path; the Postgres adapter is a skeleton.
- Browser automation is not included in the repo.
- Search quality is not backed by committed offline benchmark metrics.
- The app currently emits deprecation-prone patterns such as FastAPI `on_event` hooks and naive `datetime.utcnow()` calls.

## Future Improvements

- Replace deprecated FastAPI lifecycle hooks with lifespan handlers.
- Replace naive UTC timestamps with timezone-aware UTC values.
- Add browser-level smoke coverage for the seeded UI flow.
- Package the demo setup into a single helper command.
- Expand or harden the optional external discovery path only after the public seeded path remains reproducible.

## Skills Demonstrated

### Backend / API Engineering
- FastAPI route design with Pydantic request and response schemas
- versioned API surface for search, artifact retrieval, policy checks, and admin metrics
- background worker pattern for asynchronous artifact resolution

### Data / Storage Systems
- DuckDB-backed local catalog storage
- relational modeling for datasets, artifacts, jobs, events, signals, and search documents
- fixture-driven demo database generation for reproducible local runs

### Search / Discovery
- metadata and README-text search over dataset records
- DuckDB FTS path with LIKE-based fallback matching
- filterable discovery experience across license, modality, language, and size-class metadata

### Reliability / Reproducibility
- smoke tests for API startup, health checks, search, admin metrics, and cached artifact resolution
- GitHub Actions CI for the supported seeded demo path
- clear separation between supported local demo flow and optional external Hugging Face-backed paths

### Product / System Design
- scoped public demo surface with honest claim boundaries
- lightweight static UI for search, filtering, metrics, and schema preview
- operational endpoints and admin metrics that make system behavior inspectable

## License

MIT. See [LICENSE](LICENSE).
