# Demo video script — 3:30

**Project:** VF Logistics — Autonomous Fraud Detection Agents
**Hackathon:** All Things Agentic 2026
**Track:** The Taskmaster — Autonomous Workflow Automation
**Limit:** 4:00 hard cap. This script targets 3:30.

Live URL: https://vf-fraud-detection-304507056252.asia-southeast1.run.app

---

## Before you record

Judges are told to look for proof the backend runs on Google Cloud, so have
these ready as browser tabs:

1. The dashboard, on the **Autonomous Operations** view
2. `/health` in a second tab
3. Cloud Run service page for `vf-fraud-detection` (revision list visible)
4. Firestore Data view showing the `cases` collection
5. Pub/Sub topics list showing `case-decisions`

Setup steps in the app:

- Click **Clear board** so the run starts empty
- Do *not* pre-click Inject. The whole point is that the judge sees you click
  once and then stop touching it.

One honest timing note: agent hops take 6–12 seconds each, and a full escalation
is three hops. The clean shipment finishes in about 10 seconds, all three cases
in about 30. Do not cut away during the wait — the moving cards and the event
feed are the evidence that work is happening with no input.

---

## 0:00–0:22 — The problem

> "Vietnamese logistics operators lose real money to shipment fraud that
> threshold rules cannot see. A shipping cost sixty percent under the route
> average looks like a promotion, not under-invoicing. A shipper with one
> lifetime transaction and a generic company name looks like a new customer, not
> a shell company. Catching this means reading many weak signals together — and
> then actually doing something about it, on thousands of shipments, without an
> analyst in the loop for each one."

**On screen:** dashboard header, Autonomous Operations view, empty board.

---

## 0:22–0:45 — What makes it a Taskmaster, not a chatbot

> "So this is not an agent you talk to. Shipment events arrive on Pub/Sub, and a
> worker running inside Cloud Run picks them up on its own. It scores each
> shipment for fraud, and that score decides whether compliance screening is
> even warranted. The screening decides whether to open a deep investigation.
> And at the end it acts: it releases the shipment, or assigns an analyst, or
> holds the cargo and drafts a suspicious activity report. I click once. After
> that I am a spectator."

**On screen:** slowly scroll the empty pipeline board so the six states are
readable, then settle back at the top.

---

## 0:45–0:52 — The single click

> "Three shipments, deliberately different risk profiles."

**Action:** click **Inject shipment events**.

**Then take your hands off the keyboard and say so:**

> "That is the last input I give this system."

The button confirms the injection returned in well under a second — worth
pointing at, because it proves the call is not blocking on the agents.

---

## 0:52–1:35 — Watch the fraud agent work

**On screen:** three cards appear in Queued and start moving.

> "Every card here is a case document in Firestore, and the worker claims one at
> a time under a lease. The first agent is Gemini 3.5 Flash scoring fraud
> risk — temperature pinned low, structured JSON out, so the score is a number
> the workflow can branch on rather than prose someone has to read."

Let the event feed fill. Read one line out loud as it lands, for example the
fraud score for the clean shipment.

> "The clean garment export scores five out of a hundred. That is below the
> auto-clear threshold, so the workflow stops there — no compliance call, no
> investigation. It releases the shipment and moves on. Not spending model
> budget on a clean shipment is part of the design."

**On screen:** the CLEAN card lands in Auto-cleared. Point at the
`release_shipment` entry appearing in the actions panel on the right.

---

## 1:35–2:20 — Branching, and the middle path

> "The other two score high enough to earn a compliance screen. Second agent,
> same model, different system instruction — sanctions exposure, trade
> classification, AML indicators."

Wait for both compliance results in the feed.

> "Now the two diverge, and this is the part I care about. The furniture shipment
> is underpriced by a shipper with a thin history, so fraud risk is elevated —
> but its paperwork is complete and compliance clears it. The workflow will not
> auto-release it and will not escalate it either. It assigns it to a human
> review queue, which is the honest answer for a case like that."

**On screen:** MID card lands in Held for review; `assign_analyst` appears in
the actions panel.

> "The third one is different. Dual-use pressure transducers, an eleven-day-old
> company with no tax ID, two transhipments added after booking. Fraud risk
> ninety-five, compliance says review required. That triggers the third agent."

---

## 2:20–2:55 — Extended thinking and real action

> "The investigation agent runs with an eight thousand token thinking budget.
> It is the slow one, ten to twelve seconds, and it is the only place we spend
> that. It builds the narrative — and it names the typology."

**Action:** when the DIRTY card reaches Escalated, **click the card** to open
the case trace.

> "Here is the full trace. Three agent hops, each with its real latency and the
> model that produced it. The decision, with the reason. And underneath, the
> actions this system took on my behalf: the shipment is held, an analyst is
> assigned to the financial crime queue, and a suspicious activity report is
> drafted."

> "Note the SAR is a draft. Filing a regulatory report is not something an
> autonomous agent should complete without a human signature, so that boundary
> is deliberate."

**On screen:** scroll the trace so the hops, the decision rationale, and the
action receipts are all visible.

---

## 2:55–3:20 — Proof it is running on Google Cloud

Move through the prepared tabs quickly, roughly five seconds each.

> "Cloud Run in asia-southeast1, deployed from source. CPU always allocated and
> a minimum instance, because a background worker that only runs while someone
> is watching is not a background worker — that trade is why this service gives
> up scale-to-zero."

**Tab:** Cloud Run revision list.

> "Health endpoint: the worker loop is running, and the tick counter climbs on
> its own between refreshes. Firestore is the live state store."

**Tab:** `/health`. **Refresh it once** so the judge sees `ticks` increase.

> "Every case, event and action is in Firestore. Terminal decisions publish to a
> Pub/Sub topic so an ERP or billing system downstream can react."

**Tabs:** Firestore `cases` collection, then the Pub/Sub topics list.

---

## 3:20–3:30 — Close

> "Three shipments in, three different outcomes, real actions taken, one click
> from me. Gemini 3.5 Flash on Vertex AI, Cloud Run, Firestore and Pub/Sub —
> built entirely on Google Cloud."

**On screen:** back to the pipeline board with all three cases in their terminal
columns and the KPI row visible.

---

## If a case dead-letters on camera

Do not cut. Say what it is:

> "That one failed a step and the worker is retrying it with backoff — three
> attempts and then it dead-letters rather than silently disappearing."

A visible failure path handled cleanly reads better than a suspiciously perfect
run. The retry counter and the error are both on the case trace.
