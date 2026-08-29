# VF Logistics — Autonomous Fraud Detection Agents

**Hackathon:** All Things Agentic 2026
**Track:** The Taskmaster — Autonomous Workflow Automation
**Live URL:** https://vf-fraud-detection-304507056252.asia-southeast1.run.app

A multi-agent system that screens logistics shipments for fraud, sanctions/trade
compliance violations, and runs deep-dive investigations — without a human
walking it through each step. Originally built on Snowflake Cortex, migrated to
Gemini 3.5 Flash on Vertex AI + Cloud Run.

---

## The problem

Vietnamese logistics operators lose money to shipment fraud that is invisible to
threshold rules: a shipping cost 60% under the historical route average looks
like a promo, not under-invoicing. A shipper with 2 lifetime transactions and a
generic company name looks like a new customer, not a shell entity. Catching
these requires reading many weak signals *together* — exactly what a rules
engine cannot do and an analyst has no time to do at volume.

## What the system does

Three specialised agents, each with its own system instruction and reasoning
budget, share one shipment record:

| Agent | Responsibility | Notable config |
|---|---|---|
| **Fraud Detection** | Price manipulation, route fraud, weight/dimension fraud, document fraud, identity fraud, duplicate & time fraud. Emits `risk_score` 0–100, `risk_level`, `flags[]`, `recommendations[]`, `confidence`. | `temperature=0.1` for stable scoring |
| **Compliance Screening** | Sanctions exposure (OFAC/UN/EU patterns), trade & regulatory compliance, AML indicators, entity screening. | `temperature=0.1`, structured JSON |
| **AI Investigation** | Multi-step case investigation across related shipments, pattern analysis, network mapping, consolidated reporting. | **Extended thinking** — `thinking_budget=8000` |

All three return strict JSON (`response_mime_type="application/json"`), so
downstream routing is machine-readable rather than prose that needs parsing.

---

## Architecture

```
                    Browser (static/index.html)
                      │  fetch() JSON
                      ▼
      ┌───────────────────────────────────────────┐
      │  Cloud Run  ·  asia-southeast1            │
      │  vf-fraud-detection                       │
      │                                           │
      │  gunicorn ──► Flask (main.py)             │
      │                 │                         │
      │                 ├─ /                UI    │
      │                 ├─ /health               │
      │                 ├─ /agents               │
      │                 ├─ /demo                 │
      │                 └─ /api/v1/**            │
      │                      │                    │
      │      agents/ (google-genai SDK, async)    │
      │       ├─ fraud_detection_agent.py         │
      │       ├─ compliance_agent.py              │
      │       └─ investigation_agent.py           │
      └───────────────────┬───────────────────────┘
                          │  Vertex AI (vertexai=True)
                          ▼
              ┌───────────────────────────┐
              │  Gemini 3.5 Flash         │
              │  location: global         │
              └───────────────────────────┘
```

See `docs/architecture.png` for the diagram submitted to Devpost.

### Why these choices

- **`location="global"`** — Gemini 3.5 Flash is served from the global endpoint;
  regional endpoints (`us-central1`, `asia-southeast1`) return `404 NOT_FOUND`
  for this model. The Cloud Run service itself stays in `asia-southeast1`, close
  to users in Vietnam.
- **Async SDK calls** (`client.aio.models.generate_content`) with gunicorn
  `--threads 8` — a single instance handles concurrent analyses while each waits
  on model latency.
- **Scale to zero** — no `--min-instances`, so an idle demo costs nothing.
- **Stateless service** — all state lives in the request. No database is
  provisioned, which keeps the failure surface and the bill small.

---

## Tech stack

| Layer | Choice |
|---|---|
| Model | **Gemini 3.5 Flash** via **Vertex AI** |
| Agent framework | **Google GenAI SDK** (`google-genai`) |
| Google Cloud service | **Cloud Run** (source deploy → Cloud Build → Artifact Registry) |
| Web | Flask + gunicorn, flask-cors |
| Frontend | Vanilla HTML/CSS/JS, no build step |
| Runtime | Python 3.11-slim container |

Requirement check against the hackathon rules:

- ✅ Gemini 3.5 or newer, via Vertex AI → `gemini-3.5-flash`
- ✅ At least one Google agent framework → Google GenAI SDK
- ✅ At least one Google Cloud infrastructure service → Cloud Run

> `requirements.txt` also pins `google-cloud-firestore`, `google-cloud-pubsub`,
> `google-cloud-bigquery` and `google-cloud-storage`. These are **not used by
> the current code path** — they are held for the event-driven ingestion work
> described under *Roadmap*. Nothing in this repo reads or writes them.

---

## API

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Web dashboard (HTML) |
| `/health` | GET | Health check JSON |
| `/agents` | GET | Agent metadata & capabilities |
| `/demo` | GET | Runs the fraud agent on a built-in sample shipment |
| `/api/v1/fraud/analyze` | POST | Analyse one shipment |
| `/api/v1/fraud/batch` | POST | Analyse many — body `{"shipments":[...]}` |
| `/api/v1/compliance/screen` | POST | Compliance screening for a shipment |
| `/api/v1/compliance/entity` | POST | Screen a single entity |
| `/api/v1/investigation/case` | POST | Deep-dive investigation |
| `/api/v1/investigation/report` | POST | Consolidated report — body `{"investigations":[...]}` |

### Example

```bash
curl -s -X POST \
  https://vf-fraud-detection-304507056252.asia-southeast1.run.app/api/v1/fraud/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "shipment_id": "VF-2026-0001",
    "origin": "Ho Chi Minh City",
    "destination": "Hanoi",
    "weight_kg": 150,
    "declared_value": 50000000,
    "shipping_cost": 1200000,
    "avg_route_cost": 3000000,
    "shipper_name": "Thanh Phat Trading Co",
    "receiver_name": "Minh Long Import Ltd",
    "shipper_tx_count": 2,
    "status": "pending",
    "route_details": "HCMC to Hanoi"
  }'
```

Response (`analysis` is a JSON string produced by the model):

```json
{
  "shipment_id": "VF-2026-0001",
  "model": "gemini-3.5-flash",
  "analyzed_at": "2026-08-29T07:10:00.000000",
  "analysis": "{\"risk_score\":78,\"risk_level\":\"HIGH\",\"flags\":[...],\"recommendations\":[...],\"confidence\":0.9}"
}
```

---

## Spin-up instructions

### Prerequisites

- Python 3.11+
- `gcloud` CLI
- A Google Cloud project with billing enabled

### 1. Run locally

```bash
git clone <this-repo>
cd vf-logistics-hackathon-google

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

Authenticate so the GenAI SDK can reach Vertex AI:

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

Configure and start:

```bash
cp .env.example .env       # Windows: copy .env.example .env
# set PROJECT_ID=YOUR_PROJECT_ID and LOCATION=global

python main.py             # http://localhost:8080
```

### 2. Deploy to Cloud Run

Enable the APIs:

```bash
gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --project YOUR_PROJECT_ID
```

Grant the default compute service account the roles it needs. **This step is
required** — source deploys fail without the first three, and every model call
returns `403 PERMISSION_DENIED` without `aiplatform.user`:

```bash
PROJECT_ID=YOUR_PROJECT_ID
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
SA="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

for ROLE in \
  roles/aiplatform.user \
  roles/storage.objectAdmin \
  roles/artifactregistry.writer \
  roles/logging.logWriter
do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA" --role="$ROLE"
done
```

Deploy:

```bash
gcloud run deploy vf-fraud-detection \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --memory 2Gi --cpu 2 --timeout 300 \
  --set-env-vars "PROJECT_ID=$PROJECT_ID,LOCATION=global"
```

Verify:

```bash
BASE=$(gcloud run services describe vf-fraud-detection \
  --region asia-southeast1 --format='value(status.url)')

curl -s $BASE/health
curl -s $BASE/agents
curl -s $BASE/demo
```

Open `$BASE` in a browser for the dashboard.

### 3. Tear down

```bash
gcloud run services delete vf-fraud-detection --region asia-southeast1
```

---

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `PROJECT_ID` | GCP project used for Vertex AI | `project-93ded24f-21c3-4f1b-a7d` |
| `LOCATION` | Vertex AI location — must be `global` for Gemini 3.5 Flash | `global` |
| `PORT` | Port gunicorn binds to (set by Cloud Run) | `8080` |

The model ID is pinned in code (`MODEL_ID = "gemini-3.5-flash"`) in each agent
module rather than read from the environment, so a misconfigured deploy cannot
silently downgrade to a model the hackathon rules disallow.

---

## Findings & learnings

**Gemini 3.5 Flash is not on regional endpoints.** `us-central1` and
`asia-southeast1` both returned `404 NOT_FOUND` for
`publishers/google/models/gemini-3.5-flash`. Only `locations/global` served it.
The 404 message ("was not found **or your project does not have access to it**")
reads like an entitlement problem, which sent us looking at IAM before we
checked the endpoint — worth knowing.

**`ThinkingConfig` field is `thinking_budget`, not `thinking_budget_tokens`.**
The wrong name raises a pydantic validation error *before* any network call, so
the endpoint failed in ~3 ms. That latency in the Cloud Run request log is the
tell: a model failure would have taken seconds. We found the real field with
`python -c "import google.genai.types as t; print(list(t.ThinkingConfig.model_fields))"`.

**Cloud Build source deploys need three separate grants.** The default compute
service account needs `storage.objectAdmin` (read the uploaded source zip),
`artifactregistry.writer` (push the image) and `logging.logWriter` (or build
logs vanish, which is how we ended up debugging a "FAILURE" build with no log
output at all). A build whose docker step reports `SUCCESS` but produces no
entry under `results.images` has failed at push, not at build.

**Prompting for `response_mime_type="application/json"` is what makes the
multi-agent hand-off practical.** Each agent's output is consumed as data, not
re-parsed prose, so adding a fourth agent is a routing change rather than a
parsing project.

**Migration insight:** the Snowflake Cortex version expressed fraud rules as SQL
predicates over historical aggregates. Moving to Gemini let us delete most of
that and describe the *intent* instead — but it also means the output is no
longer deterministic, so `temperature=0.1` and an explicit `confidence` field in
the schema are doing real work.

---

## Roadmap

The current build is request-driven: the UI or an API client triggers an
analysis. The natural next step for the Taskmaster track is fully event-driven
ingestion — Pub/Sub topic on shipment-created events, a Cloud Run push
subscription that routes to the right agent based on the fraud agent's
`risk_level`, Firestore for case state across the investigation lifecycle, and
BigQuery for the historical route-cost baselines the agents currently receive as
request fields. The client libraries are already pinned for this.

---

## Repository layout

```
.
├── main.py                       Flask app, routes, async bridge
├── agents/
│   ├── __init__.py               Public agent API
│   ├── fraud_detection_agent.py  Fraud scoring
│   ├── compliance_agent.py       Sanctions / trade / AML
│   └── investigation_agent.py    Deep-dive, extended thinking
├── static/
│   └── index.html                Dashboard (no build step)
├── Dockerfile                    python:3.11-slim + gunicorn
├── cloudbuild.yaml               Cloud Build config
├── requirements.txt
├── .env.example
└── README.md
```

## License

MIT — hackathon project, 2026.
