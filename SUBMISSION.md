# Devpost Submission — VF Logistics Autonomous Fraud Detection

Copy-paste material for the Devpost form, plus the demo video script.

---

## Project name

VF Logistics — Fraud Detection an Operator Can Delegate To

## Elevator pitch (200 char limit on Devpost)

Four Gemini agents screen shipments for fraud and sanctions, but the operator—not the agents—decides what they may do about it. A published Delegation Boundary is the only source of authority.

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

But detecting fraud is only half the problem. The harder question is: **who
decides what the agent may do about it?** An agent that reasons well is not the
same as an agent you can hand authority to.

### What we built

A multi-agent system on Cloud Run where **four** specialised Gemini agents share
one shipment record, each with its own model, system instruction, sampling
temperature and reasoning budget—and a **governance layer** that determines
which of those agents' recommendations actually execute.

**Document Intake Agent** — reads a real shipping document (bill of lading,
commercial invoice, packing list) using Gemini's native PDF and image support.
Transcribes into the structured shipment record the rest of the pipeline
understands. Runs at `temperature=0.0` because this is transcription, not
generation.

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
genuinely needs multi-hop reasoning rather than a single pass. It is also the one
agent that runs on **Gemini 3.5 Flash-Lite** rather than Flash — see below.

### Two models, chosen per task

The model is not a single global setting in this system. Document intake, fraud
detection and compliance screening run **Gemini 3.5 Flash**: intake needs native
multimodal PDF reading, and fraud and compliance produce the scores that hold or
release physical cargo, so they get the stronger model.

Investigation runs **Gemini 3.5 Flash-Lite**. By the time a case reaches it the
fraud and compliance findings already exist — investigation synthesises and
summarises them rather than making the primary judgement. Flash-Lite is half the
input and half the output cost for that shape of work, and it still accepts
`thinking_budget`, so the multi-hop reasoning the case write-up needs survives
the downgrade.

Both models are reached through the same `google-genai` client with
`vertexai=True`, so the split adds no integration surface. Every agent response
envelope records the model that produced it, and the dashboard's per-case trace
shows it on each hop — the split is observable, not just asserted.

Every agent is constrained to `response_mime_type="application/json"`, so each
output is data the next stage can route on rather than prose someone has to
re-parse.

### Governance: the part most agent systems skip

Most agent demonstrations treat "the model decided" as the end of the story.
We treat it as the beginning of a different question: **who authorised that
decision?**

The answer in this system is a **Delegation Boundary**: a versioned,
machine-readable policy published by a named human. The boundary says exactly
which actions the agent may take (`release_shipment`, `hold_shipment`,
`assign_analyst`, `draft_sar`, `notify_webhook`, `publish_decision`) and within
what limits—maximum declared value, maximum effective risk, forbidden HS
prefixes, forbidden destinations. Publishing a new version marks the previous
one **SUPERSEDED**. Every executed action records the boundary version that
permitted it.

The boundary enforces a simple rule: **an agent may raise risk, never lower it
below a deterministic floor.** `verifier.py` computes that floor from arithmetic
and code-resident reference lists (lane freight baselines, dual-use HS prefixes,
enhanced due diligence destinations). A successful prompt injection can
manipulate the model's score; it cannot manipulate the floor, because the floor
does not come from the model.

With no active boundary the entire system is **SUSPENDED**. Analysis keeps
running—the agents will still tell you what they found—but protected actions are
refused. A fresh deployment can look but cannot touch until a human has
published authority.

This is what "governed autonomous" means: the agent is fully autonomous *inside*
the boundary and stops at its edge.

### Input security: documents are untrusted

A shipping document is attacker-controlled. It arrives as a PDF, goes into a
model, and the model's output moves physical cargo. We treat it as a
prompt-injection channel.

**Google Cloud Model Armor** screens the document before Gemini sees it. For a
PDF with a text layer, pypdf extracts the text deterministically, Model Armor
screens that, and a blocked document produces **no model processing at all**.
For a scanned image there is no text layer to pre-screen; the transcription is
screened after, which is a weaker assurance the case records explicitly.

The screen uses **windowed analysis**: the same 275-character injection that
triggers MEDIUM_AND_ABOVE when sent alone scored NO_MATCH when buried in a
four-page bill of lading. Documents are therefore screened in 400-character
windows with 120-character overlap, in addition to the full text.

After transcription, `untrusted.py` enforces a **strict field whitelist**.
`avg_route_cost` and `shipper_tx_count` are deliberately excluded—a document
that could state its own shipper's history would defeat the thin-history check
by claiming a long one. `risk_score`, `decision`, and `state` are **forbidden
fields**; any document attempting to set them is logged and flagged for human
review.

### Scale-to-zero without losing work

The service runs with `WORKER_MODE=ondemand` and `--min-instances=0`. No
background loop, no hourly billing. Cases advance inside request handlers: a
Pub/Sub push drives its own case to completion; the dashboard's state poll
drains a step at a time.

Failures retry with 5s/10s/20s exponential backoff and dead-letter after three
attempts. Claims are leases, so a case held by an instance that crashes or is
replaced mid-rollout is picked up by the next worker.

### Measured on the deployed service

One click and no further input:

| Shipment | Fraud risk | Compliance | Outcome | Actions executed |
|---|---|---|---|---|
| Clean garment export | 5/100 | not needed | `AUTO_CLEARED` | released for delivery |
| Underpriced furniture, thin history | 58/100 | cleared | `HELD_FOR_REVIEW` | analyst assigned |
| Dual-use goods, 11-day-old shell company | 95/100 | review required | `ESCALATED` | held, SAR drafted, compliance notified, decision published |

All three reached terminal state in roughly 30 seconds. Average agent hop was
7.3 seconds across six Gemini calls.

### Features and functionality

- **Four specialised agents on two models** — document intake, fraud detection
  and compliance on Gemini 3.5 Flash; investigation on Gemini 3.5 Flash-Lite
  with extended thinking
- **Autonomous multi-step workflow** — conditional routing with no human
  step-through
- **Delegation Boundary** — versioned policy published by a named human; the
  only source of authority for protected actions
- **Fail-closed execution gate** — no boundary, no execution; SUSPENDED state
  refuses protected actions while analysis continues
- **Deterministic risk floor** — arithmetic and code-resident lists constrain
  what the agent can claim; `effective_risk = max(model_risk, floor)`
- **Model Armor integration** — windowed screening catches injections diluted by
  surrounding document text
- **Untrusted input gate** — schema whitelist, forbidden fields, invisible
  character stripping
- **Document intake** — Gemini 3.5 Flash reads PDFs and images natively; no
  separate OCR step
- **Identity split** — `vf-fraud-detection` has `aiplatform.user` + `datastore.user`
  + `storage.objectAdmin` but no `pubsub.publisher`; `vf-executor` has no
  `aiplatform.user` — neither service can do everything
- **Scale-to-zero** — `--min-instances=0`, `WORKER_MODE=ondemand`, lease-based
  claiming, exponential backoff
- **Human review queue** — cases that hit the boundary's limits or non-waivable
  triggers go to a named reviewer; SAR drafts require human signoff
- **Live operations dashboard** — pipeline board, event feed, action log, and a
  per-case trace showing every agent hop with its real latency
- **Decision Packs** — four synthesised views (integrity/pricing, sanctions,
  exposure/counterparty, document chain) so the reviewer sees conclusions and
  disagreements, not six raw payloads
- Three independent agents also exposed behind a versioned REST API (`/api/v1/**`)
- Batch analysis, standalone entity screening, consolidated report generation
- `/demo` endpoint that runs a built-in sample so a judge needs zero setup
- Structured JSON contract on every agent output, parsed server-side

### Technologies used

| Layer | Choice |
|---|---|
| Model | Gemini 3.5 Flash (`gemini-3.5-flash`) for document, fraud and compliance; Gemini 3.5 Flash-Lite (`gemini-3.5-flash-lite`) for investigation — both via Vertex AI, `location=global` |
| Agent framework | Google GenAI SDK (`google-genai`), async client |
| Input security | Google Cloud Model Armor (`asia-southeast1`, `vf-document-intake` template) |
| Compute | Cloud Run (source deploy → Cloud Build → Artifact Registry), `--min-instances=0` |
| State | Firestore Native mode in `asia-southeast1` — `cases`, `events`, `audit_log`, `boundaries` |
| Messaging | Pub/Sub — `shipment-events` inbound, `case-decisions` outbound |
| Documents | Cloud Storage — source landing zone, processed archive |
| Web | Flask + gunicorn (1 worker, 8 threads), flask-cors |
| Frontend | Vanilla HTML/CSS/JS, inline SVG gauge, no build step |
| Container | python:3.11-slim |
| Region | Cloud Run in `asia-southeast1`, close to users in Vietnam |

Hackathon requirements: Gemini 3.5 or newer via Vertex AI (two models) · a Google
agent framework (GenAI SDK) · Google Cloud infrastructure (Cloud Run, Firestore,
Pub/Sub, Cloud Storage, Model Armor) · asynchronous background operation ·
multi-step workflow · meaningful action taken on the user's behalf

### Other data sources used

None. Shipment records—including the historical route-cost baseline and the
shipper transaction count the agents reason against—are supplied per request.
The verifier falls back to code-resident lane tables when no `avg_route_cost` is
provided, which is always the case for document-sourced shipments.

### Findings and learnings

**Gemini 3.5 Flash is not served from regional endpoints.** Both `us-central1`
and `asia-southeast1` returned `404 NOT_FOUND` for
`publishers/google/models/gemini-3.5-flash`. Only `locations/global` served it.
The 404 body reads "was not found **or your project does not have access to
it**", which sent us auditing IAM before we thought to question the endpoint—
we granted `aiplatform.admin` chasing a problem that was never a permission
problem. Cloud Run stays regional; only the Vertex AI call goes global.

**A 3 ms 500 is a client-side validation error, not a model failure.** Our
investigation agent failed instantly while the other two worked. The Cloud Run
request log showed `latency=0.003279797s`—far too fast to have touched Vertex
AI. Cause: we passed `thinking_budget_tokens` to `ThinkingConfig`, but the real
field is `thinking_budget`, so pydantic rejected it before any network call.
Confirmed in one line:
`python -c "import google.genai.types as t; print(list(t.ThinkingConfig.model_fields))"`
→ `['include_thoughts', 'thinking_budget', 'thinking_level']`. Reading latency
before reading the stack trace would have saved an hour.

**A Cloud Build step can report SUCCESS while the build fails.** Two builds
showed `run-docker-build: SUCCESS` with a completed PUSH phase, yet
`status: FAILURE` and an empty Artifact Registry. The tell is
`results.buildStepImages` populated but `results.images` absent—the push
failed, not the build. It was masked because the compute service account lacked
`logging.logWriter`, so there were no build logs to read at all. Source deploys
need three distinct grants (`storage.objectAdmin` to read the uploaded zip,
`artifactregistry.writer` to push, `logging.logWriter` to be debuggable) and
Google only warns about the third one after the fact.

**Designing for LLM non-determinism traded predictability for expressiveness.**
The original approach encoded fraud rules as SQL predicates over historical
aggregates. With Gemini we deleted most of that and described intent instead—
which is why the system now catches signal combinations that SQL never could.
But the output stopped being reproducible, so `temperature=0.1` and a
model-reported `confidence` field are load-bearing, not decoration.

**Structured output is the actual multi-agent primitive.** Forcing
`response_mime_type="application/json"` on every agent is what turns three
separate model calls into a pipeline. Without it, agent hand-off becomes string
munging and the architecture stops scaling at two agents.

**Model Armor's whole-document score dilutes localised injections.** A planted
instruction scored MEDIUM_AND_ABOVE when isolated but NO_MATCH when embedded in
legitimate BOL text. Windowed screening (400 chars, 120 overlap) restores
detection without losing context.

**Model choice is a per-agent decision, not a project-wide one.** We started with
one model id shared by every agent because that is the obvious way to build it.
But the four agents are not doing the same kind of work: intake is transcription,
fraud and compliance are primary judgements on physical cargo, and investigation
is summarisation of findings that already exist. Once we separated them, the
investigation hop moved to Flash-Lite at half the token cost with no loss in the
case write-up — it still gets `thinking_budget`, and it was never the call that
decided whether cargo moves. The lesson is that "which model" is a property of
the task, and treating it as one global constant leaves cost on the table for no
correctness benefit.

**The execution gate is more important than the model.** Judges will remember
"you can publish a policy that constrains what the agent does" longer than
"Gemini scored this shipment 78." Governance is the differentiator; the model
is the commodity.

---

## Video script (~4 min)

Requirement: must show the problem, the value proposition, the app working, and
**proof the backend runs on Google Cloud**. Record unedited if you can—the
judging criteria explicitly reward a live, unedited demo.

### 0:00 – 0:30 · The problem

Open the dashboard. Do not click yet.

> "Vietnamese logistics operators lose real money to shipment fraud that
> threshold rules cannot see. This shipment is priced at 1.2 million dong
> against a 3 million dong route average—60% under. On its own that reads like
> a promotion. The shipper has two lifetime transactions. On its own, a new
> customer. It takes reading those together to see under-invoicing through a
> shell entity, and that is exactly what a SQL rules engine cannot do."

### 0:30 – 1:00 · The governance differentiator

> "But detecting fraud is only half the problem. Who decides what the agent may
> do about it? In this system, that answer is a Delegation Boundary—a versioned
> policy published by a named human. Without an active boundary, the agents can
> analyse but cannot act. Let me show you."

Click **Governance** tab. Show the current boundary or the SUSPENDED state.

> "This boundary says the agent may release shipments worth up to $25,000 with
> effective risk below 40 and zero deterministic findings. Anything outside
> these limits goes to a human. Publishing a new version supersedes the old one,
> and every action records the boundary version that permitted it."

### 1:00 – 2:00 · Document intake and Model Armor

Click **Upload Document** with a sample PDF.

> "Real shipments start as documents, not JSON. This PDF goes through Model
> Armor before Gemini sees it—Google Cloud's screening for prompt injection.
> If it flags something, no model is invoked at all."

Wait for intake to complete.

> "The Document Intake agent just read this bill of lading and transcribed it
> into a structured record. The transcription is strict: fields like risk_score
> and decision are forbidden—a document cannot nominate its own outcome."

### 2:00 – 2:45 · Autonomous workflow

Switch to **Operations** tab. The case should be progressing.

> "Watch the pipeline. Fraud detection and compliance screening run in parallel—
> that is why a case reaches a decision in half the wall time for the same
> number of model calls."

When the case reaches a terminal state:

> "This case was auto-cleared because effective risk was 12, below the boundary's
> threshold of 40, and the deterministic validation raised nothing. The agent
> proposed the outcome; the boundary permitted it; the action executed. One
> document upload, no further input."

### 2:45 – 3:15 · Proof it runs on Google Cloud

Screen-share the Google Cloud Console. Show in this order:

1. **Cloud Run** → service `vf-fraud-detection` → revision list, region
   `asia-southeast1`, and the service URL.
2. **Revision detail** → the `LOCATION=global` and `PROJECT_ID` env vars.
3. **Logs tab** → the `POST 200 /api/v1/...` entries from the calls you just
   made on camera. This is the strongest proof—the requests are timestamped
   seconds ago.
4. Optionally **Firestore** → the `boundaries` collection showing the published
   Delegation Boundary.

> "Backend is Cloud Run in asia-southeast1, model calls go to Vertex AI on the
> global endpoint. Firestore holds the cases, events, and—critically—the
> delegation boundaries that grant the agent authority."

### 3:15 – 4:00 · Architecture and close

Show `docs/architecture.png`.

> "Browser to Cloud Run to four agents on the GenAI SDK to Gemini 3.5 Flash.
> Model Armor screens documents before they reach the model. The verifier
> computes a deterministic risk floor the agent cannot override. And the
> Delegation Boundary is the only thing that grants authority to act.
>
> The load-bearing idea: the agent decides what is true, and a published
> boundary decides what it is allowed to do about it."

### Recording checklist

- [ ] Warm the service first (open `/health`) so cold start does not eat 10s of video
- [ ] Browser zoom ≥ 125% so text is legible after compression
- [ ] Cloud Run **Logs** tab shown after the live calls, not before
- [ ] Total under 4:00
- [ ] Say the model name out loud at least once
- [ ] Close all tabs with credentials or unrelated projects visible

---

## Devpost form — field-by-field answers

### Project details

**Built with** (tags, already entered): gemini, vertex-ai, google-cloud,
cloud-run, firestore, pub-sub, cloud-storage, model-armor, google-genai-sdk,
python, flask, gunicorn, asyncio, javascript, html5, ci-cd, docker

**"Try it out" links:**
- https://vf-fraud-detection-304507056252.asia-southeast1.run.app
- https://github.com/CHAUPHUOCHOA/vf-logistics-hackathon-google

### Additional info

| Field | Answer |
|---|---|
| **Submitter Type** | Individual |
| **Country of residence** | Vietnam |
| **Category** | The Taskmaster — Autonomous Workflow Automation |
| **Organization name** | *(leave blank / "N/A" — submitting as an individual)* |
| **Date started** | 08-2026 (use the real first-commit date, MM-DD-YY) |
| **Public code repo URL** | https://github.com/CHAUPHUOCHOA/vf-logistics-hackathon-google |
| **Reproducible Testing instructions in README?** | **Yes** — README → *Reproducible testing* |
| **Hosted project URL** | https://vf-fraud-detection-304507056252.asia-southeast1.run.app |
| **Testing instructions (private)** | No login required. `GET /health` to warm it, then `POST /api/v1/simulate` and poll `GET /api/v1/orchestrator/state`. Each poll advances the pipeline one step. Full walkthrough in the README's *Reproducible testing* section. |
| **Architecture diagram** | upload `docs/architecture.png` |

**Which Google SDK did you use?** → **Google Gen AI SDK** (`google-genai`)

**Which Google Cloud Service(s) did you use?** → **Cloud Run**, **Firestore**,
**Pub/Sub**, **Cloud Storage** (Vertex AI is the model platform; Model Armor is
the input-security service — select them too if the list offers them)

**Which Google AI Models did you use?** (Gemini 3.5 or newer REQUIRED; additional
models boost your score)

```
Gemini 3.5 Flash (gemini-3.5-flash) — document intake, fraud detection, compliance screening
Gemini 3.5 Flash-Lite (gemini-3.5-flash-lite) — investigation agent, extended thinking
```

> Both models are verifiable on the live service: `GET /agents` reports the model
> per agent, and every analysis response carries a `"model"` field.

**Startup Prize fields** → leave blank (submitting as an individual, not an
incorporated organisation).

**Bonus points** → optional; the *Findings & learnings* section above is
publishable as a blog post, and a social post needs
`#AllThingsAgenticHackathon`.

---

## Submission checklist

| Item | Status |
|---|---|
| Demo video ~4 min | ⬜ record using script above |
| Public code repository | ⬜ push to GitHub |
| Architecture diagram | ✅ `docs/architecture.png` |
| Devpost text description | ✅ this file |
| README with spin-up instructions | ✅ `README.md` |
| Reproducible testing instructions | ✅ `README.md` → *Reproducible testing*, 5 tests |
| Hosted project URL | ✅ live on Cloud Run |
| Gemini 3.5+ via Vertex AI | ✅ `gemini-3.5-flash` + `gemini-3.5-flash-lite` |
| Google agent framework | ✅ Google GenAI SDK |
| Google Cloud infra service | ✅ Cloud Run, Firestore, Pub/Sub, Cloud Storage, Model Armor |

### Bonus (optional)

| Item | Status |
|---|---|
| Blog / video about the build | ⬜ the *Findings & learnings* section is already a post |
| Social post with `#AllThingsAgenticHackathon` | ⬜ |
| Additional Google AI model | ✅ **Gemini 3.5 Flash-Lite** alongside Flash — investigation agent |

If the repository is private, share it with `testing@devpost.com` and
`cloudhackathons@google.com`.

---

## Cost note

The service runs with `--min-instances=0`, so it scales to zero when idle. The
rules confirm the project does **not** need to be live at judging time—the
video and repo are the proof. After recording, you can delete it:

```bash
gcloud run services delete vf-fraud-detection --region asia-southeast1
```
