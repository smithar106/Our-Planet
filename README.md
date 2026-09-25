# PLANET — Live Earth Intelligence

> **An AI agent watching Earth.**

PLANET is an autonomous public intelligence system that continuously monitors
trusted global Earth-event data, detects meaningful changes, identifies the
events that deserve attention, investigates them with structured read-only
tools, and publishes grounded explanations automatically.

It is **not** a chatbot with a map, a static dashboard, an API viewer, or an LLM
summarizing JSON. It behaves like a small autonomous intelligence system.

> **Machines filter everything. The agent investigates what matters.**

---

## Architecture

```
               ┌── USGS
               │
SOURCES ───────┼── NASA EONET
               │
               └── NASA FIRMS
                       │
                       ▼
                    INGEST
                       │
                       ▼
                   NORMALIZE
                       │
                       ▼
                STATE COMPARISON
                       │
                       ▼
               SIGNIFICANCE ENGINE
                       │
              ┌────────┴─────────┐
              │                  │
           ROUTINE            NOTABLE
              │                  │
              │                  ▼
              │               AGENT
              │                  │
              │                  ▼
              │              VALIDATE
              │                  │
              └────────┬─────────┘
                       ▼
                    PUBLISH
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
         PUBLIC API          NEXT.JS UI
```

### Core loop

`INGEST → NORMALIZE → COMPARE WITH PRIOR STATE → SCORE SIGNIFICANCE → SELECT
EVENTS → AGENT INVESTIGATES → VALIDATE → PUBLISH → OBSERVE`

**The important architectural principle:** LLMs do **not** process every raw
incoming event. Deterministic software handles ingestion, normalization,
deduplication, calculations, state comparison, significance scoring, and
validation. The LLM is used only for investigation planning, read-only tool
selection, synthesis, and explanation.

---

## Repository layout

```
backend/          FastAPI application, worker, agent, tests
  app/
    ingest/       USGS, EONET, FIRMS providers + offline fixtures
    pipeline/     normalize, scoring, clustering, state, orchestrate
    agent/        read-only tools, LLM client, grounding, fallback
    brief/        daily Earth brief generator
    api/          public read-only endpoints
    worker/       APScheduler jobs + scheduler
  alembic/        database migrations
  tests/          pytest suite + eval fixtures
frontend/         Next.js 14 (App Router) + TypeScript + Tailwind + MapLibre
docker/           deployment notes
```

---

## Data sources

| Source | What | API |
| --- | --- | --- |
| **USGS** | Earthquakes | Official GeoJSON summary feed |
| **NASA EONET** | Wildfires, storms, volcanoes, floods, landslides, ice, drought, … | EONET API v3 |
| **NASA FIRMS** | Thermal anomalies (fire detections) | Area API (VIIRS_NOAA20_NRT / VIIRS_NOAA21_NRT) |

- USGS events persist source IDs so updates do not duplicate events.
- EONET categories are normalized into a controlled vocabulary and unknown
  categories map to `other`.
- FIRMS requires `NASA_FIRMS_MAP_KEY` (server-side only). We deliberately do
  **not** depend on `VIIRS_SNPP_NRT`. FIRMS returns tens of thousands of
  detections — these are **never** sent to an LLM.

### Normalized event model

Providers describe different phenomena; all converge on a common `Event` model:

```
Event {
  id, source, sourceId, category, subtype, title,
  latitude, longitude, geometry, firstObservedAt, lastObservedAt,
  status, rawSeverity, significanceScore, significanceTier,
  confidence, changeType, metrics, sourceUrl, rawPayload,
  createdAt, updatedAt
}
```

Categories use a controlled vocabulary (`earthquake`, `wildfire`, `volcano`,
`storm`, `flood`, `landslide`, `drought`, `ice`, `other`). Raw source payloads
are preserved verbatim on `source_records` for audit and debugging.

---

## Change detection

PLANET persists event state and classifies every transition deterministically:

`NEW`, `UPDATED`, `ESCALATING`, `DE-ESCALATING`, `UNCHANGED`, `CLOSED`

`event_snapshots` retains history so the UI can say *"NEW 12 MIN AGO"* or
*"ESCALATING"* instead of merely "here is an event".

---

## Significance engine

A transparent **0–100** score mapped to tiers:

| Tier | Range |
| --- | --- |
| `MAJOR` | 75–100 |
| `SIGNIFICANT` | 50–74 |
| `NOTABLE` | 25–49 |
| `ROUTINE` | 0–24 |

The LLM is **never** asked "is this important?". Formulas are category-specific:

- **Earthquake** — magnitude (strongly nonlinear, roughly `(M/9)^3.5`), depth,
  felt reports, USGS significance, alert level, tsunami flag, change.
- **Wildfire (FIRMS cluster)** — detection count (log-scaled), FRP, confidence
  distribution, growth since previous run.
- **EONET** — category weight, source count, persistence.

> PLANET significance is an **application-level prioritization score**, not an
> official hazard/risk classification. This is stated explicitly in the UI.

---

## Fire clustering

FIRMS detections are clustered deterministically using a single-pass greedy
algorithm with a fixed haversine radius (default **5 km**, configurable via
`FIRE_CLUSTER_RADIUS_KM`). Detections are sorted by position and time so results
are reproducible. Each cluster derives: centroid, detection count, bounding box,
mean/max FRP, confidence distribution, first/last detection, and growth vs. the
previous run.

> A FIRMS thermal anomaly is **not** a confirmed wildfire — the UI says so.

---

## Agent investigation

Only events crossing a configurable threshold are investigated
(`significance_score >= AGENT_THRESHOLD`, or `change_type == ESCALATING`, or a
tsunami flag).

The agent has **read-only** tools:

`get_event`, `get_event_history`, `get_recent_events`, `get_nearby_events`,
`get_source_record`, `get_fire_cluster_history`,
`compare_event_to_recent_activity`, `get_global_summary`

The agent has **no write access to the database**. Output is structured JSON:

```json
{
  "headline": "...",
  "summary": "...",
  "why_notable": ["...", "..."],
  "watch_next": ["...", "..."],
  "source_claims": [{"source": "...", "url": "...", "claim": "..."}]
}
```

---

## Grounded generation

> *Model output is a proposal to validate, not truth to display.*

- **Numeric grounding** — numbers in generated prose must be traceable to
  source records, deterministic calculations, or tool outputs.
- **Claim restrictions** — words like `record`, `unprecedented`, `deadly`,
  `catastrophic`, `historic`, `caused by`, `will cause`, `safe`, `dangerous`
  are rejected unless an explicit trusted source establishes them.
- Never generate casualty counts or damage claims from magnitude/anomaly data.

### Deterministic fallback

If AI generation fails validation (or no LLM is configured), PLANET publishes a
deterministic description built only from verified fields. The public site never
depends on the LLM succeeding — failure yields *less sophisticated but still
correct* output.

---

## Observability

A lightweight span-based tracer wraps the pipeline run: USGS/EONET/FIRMS fetch,
normalize, deduplicate, compare, score, select, investigate (tool calls, LLM,
validate), publish. It tracks latency, errors, counts, and token usage.

**MLflow** — set `MLFLOW_TRACKING_URI` and each pipeline run / agent pass is
logged as an MLflow run (via the lightweight `mlflow-skinny` client). A
deployable MLflow tracking server is included in the Railway configuration
(`mlflow/` service). **Telemetry failures never break the pipeline.**

`TRACING_BACKEND` controls the in-process span tracer (`memory` / `null`).

---

## Chat — natural-language questions

An in-app assistant (`/api/chat` + the floating widget) answers questions about
live events. It uses the same read-only tools as the investigation agent and
never writes to the database. External text is treated as data, not
instructions, and the endpoint is rate-limited. Without an LLM configured, it
returns deterministic guidance instead of fabricating an answer.

---

## SQL data investigation

The agent and chat have a **read-only SQL tool** (`run_sql_query`). Queries are
single-statement, must start with `SELECT`/`WITH`, pass a keyword blocklist, and
execute inside a `READ ONLY` transaction — so even a bypassed validation cannot
write. Results are capped at 100 rows.

---

## Agent evals (SQL-backed)

`python -m app.cli eval` runs the evaluation harness and stores results in the
`agent_evals` table, queryable with plain SQL (psql, the read-only SQL tool, or
any SQL client). Cases cover grounding (unsupported numbers, restricted words),
deterministic fallback schema, SQL write-blocking, and SQL ground-truth
consistency — proving the safety architecture works.

---

## Evaluation

`backend/tests/` contains fixtures and golden cases proving the safety
architecture works:

- M3 vs M7 earthquake scoring, earthquake updates, duplicate USGS records
- new/growing wildfire clusters, closed EONET events
- unsupported LLM numbers, unsupported "record" claims, LLM unavailability
- deterministic fallback behavior, agent output schema

Run them with:

```bash
cd backend
uv venv .venv && uv pip install -e ".[dev]"
pytest -q
ruff check app tests
```

---

## Local development

### 1. Backend

```bash
cd backend
cp ../.env.example .env      # fill in values (FIRMS key, LLM key optional)
uv venv .venv
uv pip install -e ".[dev]"

# Run migrations (or init tables)
alembic upgrade head          # or: python -m app.cli initdb

# Seed deterministic fixture data (no network required)
python -m app.cli seed

# Start the API
uvicorn app.main:app --reload --port 8000

# Run the scheduler/worker (separate process)
python -m app.cli worker
```

### 2. Frontend

```bash
cd frontend
cp .env.example .env.local   # set NEXT_PUBLIC_MAPBOX_TOKEN (optional)
npm install
npm run dev                  # http://localhost:3000
```

The frontend proxies `/api/*` to the backend (`NEXT_PUBLIC_API_URL`).

---

## Environment variables

See `.env.example`. Key variables:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection string |
| `NASA_FIRMS_MAP_KEY` | FIRMS Area API key (server-side only) |
| `LLM_PROVIDER` / `LLM_MODEL` | DeepSeek by default (any OpenAI-compatible) |
| `LLM_API_KEY` / `LLM_BASE_URL` | LLM credentials |
| `AGENT_THRESHOLD` | Significance threshold triggering investigation |
| `USGS_INTERVAL_SECONDS` etc. | Provider cadences |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | Optional Mapbox public token (frontend) |

The application remains fully functional with **no LLM** and with **FIRMS
unavailable** (it degrades gracefully and marks data stale).

---

## Railway deployment

Four components deploy cleanly: **frontend**, **API**, **worker**, **PostgreSQL**.

1. **PostgreSQL** — add a Railway Postgres plugin; set `DATABASE_URL`.
2. **API** — root directory `backend`; start
   `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. **Worker** — root directory `backend`; start
   `alembic upgrade head && python -m app.cli worker`. Runs independently of the
   web process.
4. **Frontend** — root directory `frontend`; set `NEXT_PUBLIC_API_URL` and
   (optionally) `NEXT_PUBLIC_MAPBOX_TOKEN` build variables.

Dockerfiles are provided in `backend/Dockerfile` and `frontend/Dockerfile`
(frontend uses Next.js standalone output). `backend/railway.json` and
`backend/railway.worker.json` are Nixpacks configs for the API and worker.

---

## Security

- API keys are **server-side only**; no key ever reaches the client bundle.
- Public API endpoints are **read-only**; no arbitrary SQL from the public.
- The agent has **no write tools**.
- API inputs are validated; generated content is sanitized before render.
- External source text is treated as **data, not instructions** — retrieved
  content can never modify system instructions.

## Source attribution

Every public event identifies its source (USGS, NASA EONET, NASA FIRMS) and
links to the official source URL where one exists. No fake citations.

---

## Limitations

PLANET ingests a limited set of public sources and does not replace official
emergency or hazard information. FIRMS detections are thermal anomalies, not
confirmed wildfire extents. PLANET never estimates casualties, damage, or causal
attribution from magnitude/anomaly data alone.
