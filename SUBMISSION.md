# Devpost Submission — VF Logistics Autonomous Fraud Detection

Copy-paste material for the Devpost form, plus the demo video script.

---

## Project name

VF Logistics — Autonomous Fraud Detection Agents

## Elevator pitch (200 char limit on Devpost)

Three Gemini 3.5 Flash agents that screen logistics shipments for fraud, sanctions exposure and deep-dive investigation — reasoning over weak signals no rules engine can catch.

## Track

The Taskmaster — Autonomous Workflow Automation

## Hosted project URL

https://vf-fraud-detection-304507056252.asia-southeast1.run.app

---

## Text description

### The problem

Vietnamese logistics operators lose money to shipment fraud that threshold rules
cannot see. A shipping cost 60% under the historical route average looks like a
promotion, not under-invoicing. A shipper with two lifetime transactions and a
generic company name looks like a new customer, not a shell entity. A creation
timestamp in the future looks like a data-entry slip, not manipulation.

Individually each signal is weak and generates false positives. Together they
are damning. Catching that combination is what a SQL rules engine structurally
cannot do, and what a human analyst has no time to do across thousands of
shipments a day.

### What we built

A multi-agent system on Cloud Run where three specialised Gemini 3.5 Flash
agents share one shipment record, each with its own system instruction, sampling
temperature and reasoning budget:

**Fraud Detection Agent** — screens seven fraud families (price manipulation,
route fraud, weight/dimension fraud, document fraud, identity fraud, duplicate
billing, time fraud). Returns `risk_score` 0–100, `risk_level`, a `flags[]`
array with per-finding severity and evidence, `recommendations[]`, and an
explicit `confidence`. Runs at `temperature=0.1` so scoring is stable across
repeat calls on the same shipment.

**Compliance Screening Agent** — sanctions exposure against OFAC / UN / EU
patterns, trade and regulatory compliance, AML indicators, and standalone entity
screening for a counterparty.

**AI Investigation Agent** — multi-step case investigation across related
shipments, pattern analysis, network mapping and consolidated reporting. This is
the one agent given extended thinking (`thinking_budget=8000`) because case work
genuinely needs multi-hop reasoning rather than a single pass.

Every agent is constrained to `response_mime_type="application/json"`, so each
output is data the next stage can route on rather than prose someone has to
re-parse. That is what makes adding a fourth agent a routing change instead of a
parsing project.

We also shipped a dashboard (vanilla HTML/CSS/JS, no build step) that drives all
three agents live: pick an agent, fill a shipment, watch the risk gauge and the
severity-coded findings come back.

### Features and functionality

- Three independent agents behind a versioned REST API (`/api/v1/**`)
- Live web dashboard with animated risk gauge and severity-coded findings
- Batch analysis endpoint for many shipments in one call
- Standalone entity screening, separate from shipment screening
- Consolidated multi-investigation report generation
- `/demo` endpoint that runs a built-in sample so a judge needs zero setup
- `/agents` endpoint exposing each agent's model, location and capabilities
- Structured JSON contract on every agent output
- Scale-to-zero deployment — an idle demo costs nothing

### Technologies used

| Layer | Choice |
|---|---|
| Model | Gemini 3.5 Flash (`gemini-3.5-flash`) via Vertex AI, `location=global` |
| Agent framework | Google GenAI SDK (`google-genai`), async client |
| Google Cloud infrastructure | Cloud Run (source deploy → Cloud Build → Artifact Registry) |
| Web | Flask + gunicorn (1 worker, 8 threads), flask-cors |
| Frontend | Vanilla HTML/CSS/JS, inline SVG gauge, no build step |
| Container | python:3.11-slim |
| Region | Cloud Run in `asia-southeast1`, close to users in Vietnam |

Hackathon requirements: Gemini 3.5 or newer via Vertex AI ✅ · a Google agent
framework (GenAI SDK) ✅ · a Google Cloud infrastructure service (Cloud Run) ✅

### Other data sources used

None. Shipment records — including the historical route-cost baseline and the
shipper transaction count the agents reason against — are supplied per request.
Wiring those baselines to a real warehouse is described in the roadmap.

### Findings and learnings

**Gemini 3.5 Flash is not served from regional endpoints.** Both `us-central1`
and `asia-southeast1` returned `404 NOT_FOUND` for
`publishers/google/models/gemini-3.5-flash`. Only `locations/global` served it.
The 404 body reads "was not found **or your project does not have access to
it**", which sent us auditing IAM before we thought to question the endpoint —
we granted `aiplatform.admin` chasing a problem that was never a permission
problem. Cloud Run stays regional; only the Vertex AI call goes global.

**A 3 ms 500 is a client-side validation error, not a model failure.** Our
investigation agent failed instantly while the other two worked. The Cloud Run
request log showed `latency=0.003279797s` — far too fast to have touched Vertex
AI. Cause: we passed `thinking_budget_tokens` to `ThinkingConfig`, but the real
field is `thinking_budget`, so pydantic rejected it before any network call.
Confirmed in one line:
`python -c "import google.genai.types as t; print(list(t.ThinkingConfig.model_fields))"`
→ `['include_thoughts', 'thinking_budget', 'thinking_level']`. Reading latency
before reading the stack trace would have saved an hour.

**A Cloud Build step can report SUCCESS while the build fails.** Two builds
showed `run-docker-build: SUCCESS` with a completed PUSH phase, yet
`status: FAILURE` and an empty Artifact Registry. The tell is
`results.buildStepImages` populated but `results.images` absent — the push
failed, not the build. It was masked because the compute service account lacked
`logging.logWriter`, so there were no build logs to read at all. Source deploys
need three distinct grants (`storage.objectAdmin` to read the uploaded zip,
`artifactregistry.writer` to push, `logging.logWriter` to be debuggable) and
Google only warns about the third one after the fact.

**Migrating off Snowflake Cortex traded determinism for expressiveness.** The
original implementation encoded fraud rules as SQL predicates over historical
aggregates. On Gemini we deleted most of that and described intent instead —
which is why the system now catches signal combinations the SQL never could. But
the output stopped being reproducible, so `temperature=0.1` and a
model-reported `confidence` field are load-bearing, not decoration.

**Structured output is the actual multi-agent primitive.** Forcing
`response_mime_type="application/json"` on every agent is what turns three
separate model calls into a pipeline. Without it, agent hand-off becomes string
munging and the architecture stops scaling at two agents.

---

## Video script (~4 min)

Requirement: must show the problem, the value proposition, the app working, and
**proof the backend runs on Google Cloud**. Record unedited if you can — the
judging criteria explicitly reward a live, unedited demo.

### 0:00 – 0:30 · The problem

Open the dashboard. Do not click yet.

> "Vietnamese logistics operators lose real money to shipment fraud that
> threshold rules cannot see. This shipment is priced at 1.2 million dong
> against a 3 million dong route average — 60% under. On its own that reads like
> a promotion. The shipper has two lifetime transactions. On its own, a new
> customer. It takes reading those together to see under-invoicing through a
> shell entity, and that is exactly what a SQL rules engine cannot do."

### 0:30 – 1:30 · Fraud agent, live

Click **Phân tích với AI** on the Fraud Detection tab. Let it run on camera —
do not cut the wait.

> "This is Gemini 3.5 Flash on Vertex AI, reasoning over the whole record."

When results land, walk the findings:

> "Risk 78, HIGH. Three flags with severity and evidence attached. Note it did
> not just fire on price — it connected the pricing gap to the shipper's thin
> transaction history. And it reports its own confidence."

Expand **Xem JSON gốc từ API**.

> "Every agent returns strict JSON, not prose. That is what lets one agent's
> output route into the next stage as data."

### 1:30 – 2:30 · Multi-agent hand-off

Switch to **Compliance** tab, same shipment, run it.

> "Same record, different agent — sanctions exposure against OFAC, UN and EU
> patterns, trade compliance, AML indicators."

Switch to **Investigation**, run it.

> "And the investigation agent, the only one given extended thinking — 8000
> tokens of reasoning budget — because case work needs multi-hop reasoning, not
> a single pass. Three specialised agents, one shipment, no human routing
> between them."

### 2:30 – 3:20 · Proof it runs on Google Cloud

Screen-share the Google Cloud Console. Show in this order:

1. **Cloud Run** → service `vf-fraud-detection` → revision list, region
   `asia-southeast1`, and the service URL.
2. **Revision detail** → the `LOCATION=global` and `PROJECT_ID` env vars.
3. **Logs tab** → the `POST 200 /api/v1/...` entries from the calls you just
   made on camera. This is the strongest proof — the requests are timestamped
   seconds ago.
4. Optionally **Cloud Build** → the successful source-deploy build.

> "Backend is Cloud Run in asia-southeast1, model calls go to Vertex AI on the
> global endpoint — Gemini 3.5 Flash is not served regionally, which was one of
> our findings."

### 3:20 – 4:00 · Architecture and close

Show `docs/architecture.png`.

> "Browser to Cloud Run to three agents on the GenAI SDK to Gemini 3.5 Flash.
> Solid borders are deployed and what you just watched run. Dashed is roadmap —
> Pub/Sub ingestion and Firestore case state to make it fully event-driven.
> This started on Snowflake Cortex as SQL predicates over aggregates. On Gemini
> we deleted most of that and described intent instead."

### Recording checklist

- [ ] Warm the service first (open `/health`) so cold start does not eat 10s of video
- [ ] Browser zoom ≥ 125% so text is legible after compression
- [ ] Cloud Run **Logs** tab shown after the live calls, not before
- [ ] Total under 4:00
- [ ] Say the model name out loud at least once
- [ ] Close all tabs with credentials or unrelated projects visible

---

## Submission checklist

| Item | Status |
|---|---|
| Demo video ~4 min | ⬜ record using script above |
| Public code repository | ⬜ push to GitHub |
| Architecture diagram | ✅ `docs/architecture.png` |
| Devpost text description | ✅ this file |
| README with spin-up instructions | ✅ `README.md` |
| Hosted project URL | ✅ live on Cloud Run |
| Gemini 3.5+ via Vertex AI | ✅ `gemini-3.5-flash` |
| Google agent framework | ✅ Google GenAI SDK |
| Google Cloud infra service | ✅ Cloud Run |

### Bonus (optional)

| Item | Status |
|---|---|
| Blog / video about the build | ⬜ the *Findings & learnings* section is already a post |
| Social post with `#AllThingsAgenticHackathon` | ⬜ |
| Integrate Gemma / Veo / Lyria | ⬜ not attempted |

If the repository is private, share it with `testing@devpost.com` and
`cloudhackathons@google.com`.

---

## Cost note

The service has no `--min-instances`, so it scales to zero when idle. The rules
confirm the project does **not** need to be live at judging time — the video and
repo are the proof. After recording, you can delete it:

```bash
gcloud run services delete vf-fraud-detection --region asia-southeast1
```
