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

We also shipped a dashboard (vanilla HTML/CSS/JS, no build step) with two views:
an **Autonomous Operations** board where cases move through the pipeline on their
own, and a **Single Agent Console** for inspecting one agent in isolation.

**The orchestrator is the actual submission.** The three agents above are
components; what makes this a Taskmaster entry is the layer that runs them
unsupervised:

- Shipment events arrive on Pub/Sub (or via the built-in simulator) at
  `POST /api/v1/events/shipment`, which returns as soon as the case is durably
  recorded in Firestore — measured at 547ms, nowhere near an agent round trip.
- An `asyncio` worker loop inside the container claims cases and advances them
  one step at a time with **no request in flight**. Cloud Run is deployed with
  `--no-cpu-throttling --min-instances=1` specifically so this loop keeps
  running when nobody is watching.
- Routing is conditional, not a fixed chain. Fraud risk under 40 short-circuits
  to release without spending a compliance call. Risk at or above 40 earns a
  screen. A blocked or review-required screen, or risk at or above 70, opens the
  investigation. Thresholds are environment variables.
- The workflow then **acts**: `release_shipment`, `hold_shipment`,
  `assign_analyst`, `draft_sar`, `notify_webhook`, and `publish_decision` to a
  Pub/Sub topic for downstream ERP/WMS/billing. Each writes an auditable receipt.
- Failures retry with 5s/10s/20s backoff and dead-letter after three attempts
  rather than vanishing. Claims are leases, so a case held by an instance that
  crashes or is replaced mid-rollout is picked up by the next worker.

Measured on the deployed service, one click and no further input:

| Shipment | Fraud risk | Compliance | Outcome | Actions executed |
|---|---|---|---|---|
| Clean garment export | 5/100 | not needed | `AUTO_CLEARED` | released for delivery |
| Underpriced furniture, thin history | 58/100 | cleared | `HELD_FOR_REVIEW` | analyst assigned |
| Dual-use goods, 11-day-old shell company | 95/100 | review required | `ESCALATED` | held, SAR drafted, compliance notified, decision published |

All three reached terminal state in roughly 30 seconds. Average agent hop was
7.3 seconds across six Gemini calls.

### Features and functionality

- **Autonomous multi-step workflow** — conditional routing across three agents
  with no human step-through
- **Background execution** — `asyncio` worker loop advancing cases with no
  request in flight
- **Event ingestion** — one endpoint accepting both a bare shipment and a
  Pub/Sub push envelope, idempotent per `shipment_id`
- **Real actions** — shipments held or released, analysts assigned, SAR drafts
  produced, decisions published to Pub/Sub, all with audit receipts
- **Durable case state** — Firestore, so a workflow survives an instance restart
  and resumes where it stopped
- **Fault tolerance** — lease-based claiming, exponential backoff, dead-letter
  state, and a visible `last_tick_error` on `/health`
- **Live operations dashboard** — pipeline board, event feed, action log, and a
  per-case trace showing every agent hop with its real latency
- Three independent agents also exposed behind a versioned REST API (`/api/v1/**`)
- Batch analysis, standalone entity screening, consolidated report generation
- `/demo` endpoint that runs a built-in sample so a judge needs zero setup
- Structured JSON contract on every agent output, parsed server-side

### Technologies used

| Layer | Choice |
|---|---|
| Model | Gemini 3.5 Flash (`gemini-3.5-flash`) via Vertex AI, `location=global` |
| Agent framework | Google GenAI SDK (`google-genai`), async client |
| Compute | Cloud Run (source deploy → Cloud Build → Artifact Registry), CPU always allocated, `min-instances=1` |
| State | Firestore Native mode in `asia-southeast1` — `cases`, `events`, `audit_log` |
| Messaging | Pub/Sub — `shipment-events` inbound, `case-decisions` outbound |
| Web | Flask + gunicorn (1 worker, 8 threads), flask-cors |
| Frontend | Vanilla HTML/CSS/JS, inline SVG gauge, no build step |
| Container | python:3.11-slim |
| Region | Cloud Run in `asia-southeast1`, close to users in Vietnam |

Hackathon requirements: Gemini 3.5 or newer via Vertex AI · a Google agent
framework (GenAI SDK) · Google Cloud infrastructure (Cloud Run, Firestore,
Pub/Sub) · asynchronous background operation · multi-step workflow · meaningful
action taken on the user's behalf

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

**Designing for LLM non-determinism traded predictability for expressiveness.**
The original approach encoded fraud rules as SQL predicates over historical
aggregates. With Gemini we deleted most of that and described intent instead —
which is why the system now catches signal combinations that SQL never could.
But the output stopped being reproducible, so `temperature=0.1` and a
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

Click **Analyze with AI** on the Fraud Detection tab. Let it run on camera —
do not cut the wait.

> "This is Gemini 3.5 Flash on Vertex AI, reasoning over the whole record."

When results land, walk the findings:

> "Risk 78, HIGH. Three flags with severity and evidence attached. Note it did
> not just fire on price — it connected the pricing gap to the shipper's thin
> transaction history. And it reports its own confidence."

Expand **View raw JSON from API**.

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
> We designed for LLM non-determinism from the start: describe intent instead
> of SQL predicates, but lean on low temperature and explicit confidence fields."

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
