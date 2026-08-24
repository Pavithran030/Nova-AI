# Nova — AI-Powered Revenue Recovery Agent
### Complete Project Blueprint: Scratch to Final Product
#### Track 03: AI Revenue Recovery — Razorpay Hackathon

> **Project Code Name:** Nova (temporary — final name TBD)
>
> **Tagline:** *Detect. Diagnose. Recover. Prove It.*

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Solution Overview](#3-solution-overview)
4. [Unique Value Proposition](#4-unique-value-proposition)
5. [System Architecture](#5-system-architecture)
6. [End-to-End Workflow](#6-end-to-end-workflow)
7. [Detailed Data Flow](#7-detailed-data-flow)
8. [Core Features — The Four Pillars](#8-core-features--the-four-pillars)
9. [Methodology & Intelligence Layer](#9-methodology--intelligence-layer)
10. [Recovery Action Policy Table](#10-recovery-action-policy-table)
11. [NPCI Compliance & Regulatory Constraints](#11-npci-compliance--regulatory-constraints)
12. [Technology Stack](#12-technology-stack)
13. [Database Schema](#13-database-schema)
14. [API Surface](#14-api-surface)
15. [Implementation Plan — Phase by Phase](#15-implementation-plan--phase-by-phase)
16. [Dashboard & UI Design](#16-dashboard--ui-design)
17. [Evaluation Methodology](#17-evaluation-methodology)
18. [Compliance & Ethics](#18-compliance--ethics)
19. [Definition of Done](#19-definition-of-done)
20. [Demo Script](#20-demo-script)
21. [Final Pitch](#21-final-pitch)

---

## 1. Executive Summary

**Nova** is an AI-driven revenue recovery agent that detects, diagnoses, and automatically recovers lost revenue from payment failures, checkout abandonment, failed subscription renewals, and overdue B2B invoices — all within a single, coherent system.

It shifts recovery from *passive, fixed-interval retries* to **proactive, intelligent, and explainable actions**, directly increasing merchant revenue while maintaining full auditability.

Unlike fragmented point tools that handle each revenue leak in isolation, Nova owns the **full revenue-recovery lifecycle** across all leak points:

- **Classifies** why a payment or invoice is at risk (root-cause bucket, not just "failed")
- **Decides** the recovery action using a policy engine aware of NPCI's actual retry-window and attempt-count constraints
- **Executes** within a bounded, fully audited action set — nothing open-ended
- **Prioritizes** B2B collections by expected recovery value (`amount × P(payment)`)
- **Proves its value** by running a naive baseline against its own policy on the same synthetic batch, reporting the recovered-revenue delta honestly

This directly satisfies the track's stated bar: *"Don't just identify the problem. Show measured money recovered across a batch, with compliant escalation, stopping rules, and an audit trail."*

---

## 2. Problem Statement

Indian merchants lose recurring and B2B revenue at **three critical points** that are almost always handled by three disconnected, naive scripts instead of one coherent system:

### 2.1 UPI Autopay Failures
UPI Autopay mandates fail roughly **8–15% of the time** (several times the 2–3% failure rate of card mandates) — mostly from insufficient balance, bank server timeouts, or expired mandates.

Since **NPCI's August 2025 rule change**, every mandate is capped at:
- **4 total attempts** (1 original + 3 retries)
- Autopay execution restricted to specific windows: **before 10:00 AM, 1:00–5:00 PM, after 9:30 PM**

A merchant that retries blindly — outside these windows or without regard to root cause — burns its entire retry budget on the wrong problem and permanently loses that cycle's payment.

### 2.2 Checkout Payment Failures
When a payment fails mid-checkout, most customers simply abandon rather than retry. There is rarely an automated recovery flow — just a lost sale. Revenue leaks from:
- Gateway timeouts and 3DS issues
- Card declines and network errors
- User friction at the payment step

### 2.3 B2B Receivables
Overdue invoices get chased manually over email/WhatsApp/calls, usually sorted by "oldest first" or "largest first" — **not** by which invoices are actually likely to be paid if chased now. This wastes collections effort on low-probability invoices while high-value recoverable ones age out.

### The Core Problem
Each of these is usually solved (if at all) by a separate point tool:
- None of them reason about the other two
- None of them respect the regulatory retry constraints that govern UPI
- None of them report an honest, measured before/after recovery number
- Merchants lose revenue without knowing *why* or *how* to fix it

**Nova closes the loop** — from detecting the problem, to diagnosing it, to choosing the right intervention, to recovering the money — all while logging every step for compliance.

---

## 3. Solution Overview

Nova is a **single agent** that owns the full revenue-recovery lifecycle across all three leak points:

```
┌──────────────┐    ┌───────────────┐    ┌────────────────┐    ┌───────────────┐    ┌─────────────┐
│   INGEST      │ →  │  CLASSIFY     │ →  │  DECIDE         │ →  │  EXECUTE      │ →  │  AUDIT/LOG   │
│ webhook       │    │ root cause    │    │ policy engine   │    │ bounded action│    │ append-only  │
│ simulator     │    │ (rules + ML)  │    │ (NPCI-aware)    │    │ + stop rules  │    │ ledger       │
└──────────────┘    └───────────────┘    └────────────────┘    └───────────────┘    └─────────────┘
                                                                        │
                                                                        ▼
                                                               ┌────────────────┐
                                                               │ ESCALATE TO     │
                                                               │ HUMAN QUEUE     │
                                                               │ (on cap/limit)  │
                                                               └────────────────┘
```

### How It Works (Step by Step)

1. **Ingest** — A Razorpay test-mode webhook simulator emits `payment.failed`, `subscription.charged.failed`, and synthetic `invoice.overdue` events into a queue
2. **Classify** — Each event is bucketed into a root cause: insufficient balance, bank timeout, expired card, mandate expired/revoked, or (for invoices) days-overdue with payment-history context
3. **Decide** — The policy engine looks up the root-cause bucket, checks remaining retry budget and current time against NPCI's allowed windows, and picks the next action from a fixed action set
4. **Execute** — The chosen action runs (simulated SMS/WhatsApp/email dispatch, mandate re-auth link, a scheduled smart retry, or an invoice follow-up), and every action is written to the audit log **before** it fires
5. **Stop or Escalate** — If retry/contact caps are hit, or a "promise to pay" is broken past its threshold, the case moves to a human-review queue instead of continuing automatically

---

## 4. Unique Value Proposition

| Aspect | Traditional Approach | Nova |
|--------|----------------------|------|
| **Root Cause** | Not identified | Diagnosed from 100+ signals (gateway codes, user behavior, device, time, history) |
| **Recovery Action** | Fixed retries (e.g., 3 attempts every 24h) | Adaptive — based on root cause (e.g., 3DS timeout → re-prompt; balance → retry on payday) |
| **Measurability** | Only attempts logged | ₹ recovered per strategy, ROI per action, success rate per cause |
| **Audit Trail** | Minimal or none | Full trace: detection → diagnosis → action → outcome, with stopping rules |
| **Compliance** | Often unbounded | Gated with max retries, daily caps, customer opt-out, NPCI window enforcement, and escalation rules |
| **B2B Prioritization** | Oldest-first or largest-first | Expected recovery value ranking (`amount × P(payment)`) |
| **Evaluation Honesty** | Cherry-picked success stories | Baseline vs. agent comparison on identical batch, failures reported honestly |

### Why Track 03?

| Criterion | How Nova Fits |
|-----------|---------------|
| **Direct business impact** | Recovery is measured in ₹ recovered — a metric merchants and Razorpay care about deeply |
| **Razorpay's strategic focus** | Agent Studio is the future; Nova is a perfect example of a revenue-focused agent that can be published on the platform |
| **Unique AI angle** | We don't just retry — we **diagnose the root cause** and **adapt the recovery action** accordingly |
| **Clear "Bar"** | The track requires *measured money recovered*, *bounded stopping rules*, and an *audit trail* — all built into Nova from day one |

---

## 5. System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          NOVA SYSTEM                                │
│                                                                     │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────────────────┐ │
│  │  INGESTION   │   │  DIAGNOSIS    │   │    DECISION ENGINE       │ │
│  │  LAYER       │   │  LAYER        │   │    (Policy + NPCI)       │ │
│  │              │   │               │   │                          │ │
│  │ • Webhooks   │──▶│ • Rules       │──▶│ • Root-cause → Action    │ │
│  │ • Batch      │   │ • ML Model    │   │ • Retry budget check     │ │
│  │ • Simulator  │   │ • Confidence  │   │ • Time window validation │ │
│  └─────────────┘   └──────────────┘   └───────────┬──────────────┘ │
│                                                    │                │
│                                                    ▼                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    ORCHESTRATOR / EXECUTOR                    │   │
│  │                                                              │   │
│  │  • Rate limiting    • Idempotency    • Retry semantics       │   │
│  │  • Stopping rules   • Cap enforcement                        │   │
│  │                                                              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │   │
│  │  │ WhatsApp │ │  Email   │ │  Voice   │ │ Razorpay API   │  │   │
│  │  │ Business │ │ SendGrid │ │ Twilio   │ │ (Direct Retry) │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                          │                                          │
│                          ▼                                          │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  AUDIT LOGGER    │  │  METRICS     │  │  HUMAN ESCALATION    │   │
│  │  (Append-only)   │  │  (Prometheus)│  │  QUEUE               │   │
│  └─────────────────┘  └──────────────┘  └──────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    REACT/TS DASHBOARD                                │
│  • Recovery overview    • Audit log viewer    • Baseline comparison │
│  • Strategy performance • Root cause breakdown • B2B priority queue │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. End-to-End Workflow

### 6.1 Event Lifecycle

```
  Payment Event Arrives
          │
          ▼
    ┌───────────┐
    │  Source?   │
    └─────┬─────┘
          │
    ┌─────┴──────────────────────────┐
    │                                │
    ▼                                ▼
  Real-time Webhook              Batch Job
  (payment.failed /              (Abandoned carts /
   subscription.charge.failed)    Overdue invoices)
    │                                │
    └──────────┬─────────────────────┘
               ▼
       Feature Extraction
               │
               ▼
    ┌──────────────────┐
    │ Rule-based        │
    │ Classification    │
    └────────┬─────────┘
             │
    ┌────────┴──────────┐
    │                   │
    ▼                   ▼
  Mapped to          Ambiguous/Unknown
  known code              │
    │                     ▼
    │              ML Classifier
    │                     │
    │           ┌─────────┴─────────┐
    │           │                   │
    │           ▼                   ▼
    │     Confidence ≥ 0.7    Confidence < 0.7
    │           │                   │
    │           │                   ▼
    │           │            Generic Retry +
    │           │            Human Flag
    └─────┬─────┘
          ▼
    Root Cause Assigned
          │
          ▼
    Policy Engine Lookup
          │
          ▼
    ┌──────────────┐
    │ NPCI Window   │
    │ Check         │
    └──────┬───────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
  Valid         Outside
  window        window
    │             │
    ▼             ▼
  Retry        Schedule for
  Budget       Next Valid
  Check        Window
    │
    ┌──────┴──────┐
    │             │
    ▼             ▼
  Budget       Budget
  remaining    exhausted
    │             │
    ▼             ▼
  Execute      Escalate to
  Action       Human Queue
    │
    ▼
  Log to Audit Trail
    │
    ▼
  ┌──────────┐
  │ Outcome? │
  └────┬─────┘
       │
  ┌────┴────┐
  │         │
  ▼         ▼
Recovered  Failed
  │         │
  ▼         ▼
Mark      More attempts?
Success     │
Update    ┌─┴──┐
Metrics   │    │
          ▼    ▼
         Yes   No → Escalate
          │
          ▼
        Back to
        Policy Engine
```

---

## 7. Detailed Data Flow

### 7.1 Ingestion Layer

1. **Real-time**: Webhooks from Razorpay for:
   - `payment.failed`
   - `subscription.charge.failed`
   - `invoice.past_due`
2. **Batch**: Daily cron job to pull abandoned carts (via Razorpay Orders API with status `created` > 1 hour)

### 7.2 Feature Store
PostgreSQL tables storing aggregated transaction history per user (90 days retention) — used for model features such as:
- Transaction amount vs. typical amount for that customer
- Historical success rate for that customer/mandate
- Time since last attempt
- Retry count so far
- Customer's historical on-time-payment rate (for B2B)

### 7.3 Detection
Rule-based triggers push events to the diagnosis queue:
- Payment failed ≥ 2 times
- Cart abandoned > 1 hour
- Invoice overdue > configured threshold

### 7.4 Diagnosis
ML model predicts root cause:
- If confidence ≥ 0.7 → proceed with adaptive action
- If confidence < 0.7 → fallback to generic retry + log for manual review

### 7.5 Decision Engine
Looks up action plan from a config table (YAML or DB) that can be updated dynamically by merchants. Maps `root_cause` → `action_sequence`.

### 7.6 Orchestrator
Schedules actions with:
- **Rate limiting** — max 2 actions per customer per day
- **Idempotency** — same transaction not acted on twice (using `transaction_id` as lock key in Redis)
- **Retry semantics** — for action-level network failures

### 7.7 Execution
Calls external services (simulated for hackathon):
- WhatsApp Business API
- SendGrid / Amazon SES for email
- Twilio for voice calls
- Razorpay API for direct retry

### 7.8 Logging & Metrics
Writes every step to audit DB (PostgreSQL) and pushes aggregated metrics to Prometheus.

---

## 8. Core Features — The Four Pillars

### Pillar 1: Intelligent Root-Cause Analysis

- **Input**: Transaction data (amount, gateway response code, user_id, device fingerprint, time of day, previous attempt count, subscription tenure, etc.)
- **Model**: Multi-class classifier (XGBoost or Logistic Regression) trained on historical payment logs to predict the primary failure reason
- **Output Classes**:

| Class | Description |
|-------|-------------|
| `INSUFFICIENT_FUNDS` | Balance low at the time of debit |
| `BANK_TIMEOUT` | 3DS / bank gateway timeout |
| `RISK_DECLINE` | Flagged by fraud rules (potential false positive) |
| `NETWORK_ERROR` | Transient network issue |
| `CARD_EXPIRED` | Expired card on file |
| `MANDATE_REVOKED` | Mandate revoked or expired by customer/bank |
| `ABANDONMENT` | Cart not checked out |
| `OVERDUE` | B2B invoice past due date |

- **Confidence threshold**: If model confidence < 0.7, fallback to generic retry with human-in-the-loop flag
- **Explainability**: Log the *reason* for every classification, not just the label — this is what makes the decision auditable later

#### Classification Pipeline

- **First pass (rules):** Map Razorpay/bank error codes directly to buckets (e.g., `INSUFFICIENT_FUNDS`, `BANK_TIMEOUT`, `CARD_EXPIRED`, `MANDATE_REVOKED`)
- **Second pass (lightweight ML):** For ambiguous or unmapped codes, use a small gradient-boosted classifier with features like: retry count, time since last attempt, transaction amount vs. typical amount, historical success rate

### Pillar 2: Adaptive Recovery Workflow (Decision Engine)

Maps each root-cause class to one or more recovery actions, with priority, timing, and conditions. See [Section 10](#10-recovery-action-policy-table) for full policy table.

**Stopping rules (bounded execution):**
- Max **4 total attempts** per mandate (per NPCI rules)
- Max **3 retry attempts** per non-mandate transaction
- Max **2 actions** per customer per day
- Max **1 checkout nudge** per abandoned cart
- Customer can opt-out globally via a single command (e.g., "STOP")
- Escalate to merchant dashboard / human queue if recovery fails after all attempts
- Max N invoice follow-ups before mandatory escalation

### Pillar 3: Verifiable Recovery Measurement

Dashboard shows for each batch (e.g., last 7 days):
- **Total at-risk revenue** (₹) — sum of failed/abandoned amounts
- **Recovered revenue** (₹) — amount successfully recovered
- **Recovery rate** = Recovered / At-risk × 100
- **ROI per strategy** (e.g., WhatsApp recovery yields 2.3× ROI, voice yields 1.8×)
- **Failure distribution** by root cause (helps merchants fix systemic issues)
- **Baseline vs. Agent comparison** — side by side, same batch

All metrics are computed on the full test set, not cherry-picked — honesty is baked in.

### Pillar 4: Compliant Audit Trail

Every recovery attempt is logged with:

| Field | Description |
|-------|-------------|
| `timestamp` | When the action occurred |
| `transaction_id` | Which transaction this relates to |
| `root_cause` | Diagnosed cause (with model confidence) |
| `reasoning` | Why this specific action was chosen |
| `action_taken` | Including exact content sent to user |
| `channel` | WhatsApp, Email, SMS, Voice, API retry |
| `result` | success, failed, stopped |
| `stop_reason` | If stopped: max_attempts, opt_out, daily_cap, etc. |
| `actor` | `agent` vs. `human` |

All logs stored in PostgreSQL (append-only — never updated or deleted), exposed via a read-only API for merchant audit. Full transparency — no black-box decisions.

---

## 9. Methodology & Intelligence Layer

### 9.1 B2B Expected-Recovery-Value Ranking

Train a simple logistic regression (or hand-tuned scoring formula for the hackathon) on synthetic invoice history features:
- Days overdue
- Invoice size
- Customer's historical on-time-payment rate
- Count of prior broken promises

**Output:** `P(payment)` per invoice → multiply by `amount` → sort the collections queue by that **expected value** — not by due date or invoice size alone.

This single change is the clearest "we thought about this more than a to-do list" signal in the whole build.

### 9.2 Promise-to-Pay Tracker

A small state machine per invoice:

```
┌──────────┐     ┌──────────────┐     ┌───────────────┐
│ PROMISED  │ ──▶ │ DUE DATE     │ ──▶ │ PAID?         │
│           │     │ PASSED       │     │               │
└──────────┘     └──────────────┘     └───────┬───────┘
                                              │
                                     ┌────────┴────────┐
                                     │                 │
                                     ▼                 ▼
                              ┌────────────┐   ┌─────────────┐
                              │ YES: Close  │   │ NO: Increment│
                              │ case        │   │ broken_count │
                              └────────────┘   └──────┬──────┘
                                                      │
                                              ┌───────┴───────┐
                                              │               │
                                              ▼               ▼
                                    ┌──────────────┐ ┌─────────────┐
                                    │ < threshold:  │ │ ≥ threshold: │
                                    │ Re-follow-up  │ │ Escalate to  │
                                    │               │ │ human queue  │
                                    └──────────────┘ └─────────────┘
```

This is the "compliant escalation" the track's bar explicitly asks for.

### 9.3 Optional LLM Layer

Used **only** inside the fixed action set — for example:
- Drafting the *wording* of a WhatsApp/Hinglish nudge for a chosen action
- Personalizing email copy based on customer context

**Never** used to choose the action itself. Keeps the money-decision path fully deterministic and explainable.

---

## 10. Recovery Action Policy Table

| Root Cause | Recovery Action | Constraint Applied |
|---|---|---|
| **Insufficient Balance** | Delay retry to a likely salary-credit date (1st/7th of month) within an allowed NPCI window | Max 3 retries, must land in 10 AM / 1–5 PM / 9:30 PM+ windows |
| **Bank Timeout** | Immediate retry with short backoff | Counts against the same 4-attempt cap |
| **Expired/Near-Expiry Card** | Send update-payment-method link, no auto-retry | No mandate retry attempted |
| **Mandate Revoked/Expired** | Trigger re-authorization flow | One re-auth request only, then escalate |
| **Risk Decline (false positive)** | Auto-appeal with evidence package (device, location, past good history) if confidence in false positive is high | Escalate if appeal fails |
| **Checkout Abandonment** | Time-boxed reminder (single nudge) with resume-checkout link + optional personalized discount coupon | One nudge only — no repeated contact |
| **Overdue B2B Invoice** | Rank by `amount × P(payment)`, auto-send templated follow-up, track promise-to-pay | Escalate to human after N broken promises |
| **Network Error** | Immediate retry with exponential backoff | Max 3 retries |

### Detailed Action Sequences (example config)

```json
{
  "TIMEOUT": [
    {"type": "whatsapp", "template": "retry_link", "delay_minutes": 0},
    {"type": "email", "template": "retry_link", "delay_minutes": 10}
  ],
  "INSUFFICIENT_FUNDS": [
    {"type": "sms", "template": "payday_reminder", "schedule": "next_salary_date - 1 day"},
    {"type": "api_retry", "schedule": "next_salary_date", "npci_window": true}
  ],
  "CARD_EXPIRED": [
    {"type": "email", "template": "update_card_link", "delay_minutes": 0},
    {"type": "whatsapp", "template": "update_card_link", "delay_minutes": 60}
  ],
  "OVERDUE": [
    {"type": "whatsapp", "template": "gentle_reminder", "delay_minutes": 0},
    {"type": "voice_call", "template": "payment_reminder", "delay_days": 3}
  ]
}
```

---

## 11. NPCI Compliance & Regulatory Constraints

> **Critical:** These constraints are hard-coded in the system, not just policy. Violation means lost retry budget and potential regulatory issues.

### UPI Autopay Rules (Post-August 2025)

| Rule | Constraint |
|------|-----------|
| **Total attempts** | 4 maximum (1 original + 3 retries) |
| **Allowed windows** | Before 10:00 AM, 1:00 PM – 5:00 PM, After 9:30 PM |
| **Window enforcement** | System blocks any retry outside these windows; schedules for next valid window instead |
| **Budget tracking** | Each attempt (including timed-out ones) counts against the 4-attempt cap |

### General Compliance Rules

| Rule | Implementation |
|------|---------------|
| **No overcharging** | No action can exceed the original transaction amount |
| **Opt-out** | Every communication includes a clear opt-out mechanism (e.g., "Reply STOP to unsubscribe") |
| **Daily caps** | Max 2 actions per customer per day |
| **Escalation** | Mandatory human handoff when automated limits are reached |
| **Audit readiness** | Every action is logged and explainable |

> ⚠️ *NPCI retry-cap and time-window figures reflect the August 2025 rule change as reported publicly. Verify current figures against official NPCI/Razorpay documentation before treating them as production-accurate.*

---

## 12. Technology Stack

| Layer | Technology | Why |
|-------|------------|-----|
| **Frontend** | React + TypeScript + Vite, Chart.js | Fast, type-safe, beautiful dashboard with charts. Hot module replacement for rapid dev. |
| **Styling** | CSS (or Tailwind CSS if preferred) | Clean, responsive UI |
| **Backend API** | Python 3.10+ with FastAPI | High performance, automatic OpenAPI docs, async support |
| **ML / AI** | Scikit-learn / XGBoost for classification; LangChain for LLM-generated content (optional) | Battle-tested for tabular data; LLM for personalized copy |
| **Database** | PostgreSQL (with TimescaleDB extension for time-series) | ACID compliance, robust, supports time-series queries |
| **Cache / Queue** | Redis (for Celery broker and result backend) | Fast, reliable, widely used |
| **Async Workers** | Celery | Distributed task queue for recovery actions |
| **Monitoring** | Prometheus + Grafana | Real-time metrics and alerts |
| **External Integrations** | Razorpay API, WhatsApp Business API, Twilio, SendGrid | All production-grade services (simulated for hackathon) |
| **Deployment** | Docker + Docker Compose (local); Kubernetes (production) | Portable, scalable |

### Project Directory Structure

```
Nova/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── config.py               # Environment & app config
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── transaction.py      # SQLAlchemy models
│   │   │   ├── mandate.py
│   │   │   ├── invoice.py
│   │   │   ├── recovery_action.py
│   │   │   ├── audit_log.py
│   │   │   └── policy_config.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── webhook.py          # Pydantic schemas
│   │   │   ├── recovery.py
│   │   │   └── report.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── classifier.py       # Root-cause classification
│   │   │   ├── policy_engine.py    # Decision engine
│   │   │   ├── executor.py         # Action execution
│   │   │   ├── orchestrator.py     # Rate limiting, idempotency
│   │   │   ├── scorer.py           # B2B expected-value scoring
│   │   │   └── promise_tracker.py  # Promise-to-pay state machine
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── webhooks.py         # Webhook ingestion endpoints
│   │   │   ├── recovery.py         # Recovery queue & execution
│   │   │   ├── audit.py            # Audit trail endpoints
│   │   │   └── reports.py          # Baseline vs agent comparison
│   │   ├── ml/
│   │   │   ├── train_classifier.py # Train root-cause model
│   │   │   ├── train_scorer.py     # Train B2B scoring model
│   │   │   └── models/             # Saved .pkl model files
│   │   ├── workers/
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py       # Celery configuration
│   │   │   └── tasks.py            # Async recovery tasks
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── npci.py             # NPCI window & cap validation
│   │       ├── synthetic_data.py   # Synthetic data generator
│   │       └── baseline.py         # Naive baseline policy
│   ├── tests/
│   │   ├── test_classifier.py
│   │   ├── test_policy_engine.py
│   │   ├── test_orchestrator.py
│   │   └── test_npci.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic/                    # Database migrations
│       └── ...
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── components/
│   │   │   ├── Dashboard.tsx       # Main overview
│   │   │   ├── RecoveryQueue.tsx   # Prioritized action queue
│   │   │   ├── AuditViewer.tsx     # Full audit trail viewer
│   │   │   ├── ComparisonView.tsx  # Baseline vs agent
│   │   │   ├── StrategyChart.tsx   # ROI per channel
│   │   │   └── RootCauseChart.tsx  # Failure distribution
│   │   ├── hooks/
│   │   ├── services/
│   │   │   └── api.ts              # API client
│   │   └── types/
│   │       └── index.ts            # TypeScript interfaces
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml              # PostgreSQL, Redis, backend, frontend
├── NOVA_PROJECT_BLUEPRINT.md       # This file
└── README.md
```

---

## 13. Database Schema

```sql
-- Core entities
CREATE TABLE merchants (
    id              UUID PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    tenant_id       VARCHAR(100) UNIQUE,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE mandates (
    id              UUID PRIMARY KEY,
    merchant_id     UUID REFERENCES merchants(id),
    customer_id     VARCHAR(255) NOT NULL,
    status          VARCHAR(50) NOT NULL,          -- active, expired, revoked
    expiry_date     DATE,
    max_attempts    INT DEFAULT 4,
    attempts_used   INT DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE transactions (
    id              UUID PRIMARY KEY,
    merchant_id     UUID REFERENCES merchants(id),
    amount          DECIMAL(12,2) NOT NULL,
    currency        VARCHAR(3) DEFAULT 'INR',
    status          VARCHAR(50) NOT NULL,          -- pending, failed, recovered, abandoned
    error_code      VARCHAR(100),
    error_description TEXT,
    mandate_id      UUID REFERENCES mandates(id),
    attempt_count   INT DEFAULT 0,
    max_attempts    INT DEFAULT 4,
    last_attempt_at TIMESTAMP,
    customer_id     VARCHAR(255),
    device_fingerprint VARCHAR(255),
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE invoices (
    id              UUID PRIMARY KEY,
    merchant_id     UUID REFERENCES merchants(id),
    customer_id     VARCHAR(255) NOT NULL,
    amount          DECIMAL(12,2) NOT NULL,
    due_date        DATE NOT NULL,
    status          VARCHAR(50) NOT NULL,          -- pending, overdue, paid, escalated
    days_overdue    INT DEFAULT 0,
    broken_promise_count INT DEFAULT 0,
    payment_probability DECIMAL(5,4),              -- P(payment) from scorer
    expected_recovery_value DECIMAL(12,2),          -- amount * P(payment)
    followup_count  INT DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE recovery_actions (
    id              UUID PRIMARY KEY,
    entity_type     VARCHAR(50) NOT NULL,          -- transaction, invoice, mandate
    entity_id       UUID NOT NULL,
    root_cause      VARCHAR(100) NOT NULL,
    root_cause_confidence DECIMAL(5,4),
    action_type     VARCHAR(100) NOT NULL,         -- api_retry, whatsapp, email, voice, sms, re_auth
    channel         VARCHAR(50),
    content_sent    TEXT,                           -- exact message/content sent
    decided_at      TIMESTAMP NOT NULL,
    executed_at     TIMESTAMP,
    scheduled_for   TIMESTAMP,                     -- for delayed/scheduled actions
    outcome         VARCHAR(50),                   -- success, failed, pending, stopped
    stop_reason     VARCHAR(100),                  -- max_attempts, opt_out, daily_cap, etc.
    created_at      TIMESTAMP DEFAULT NOW()
);

-- APPEND-ONLY — never updated or deleted
CREATE TABLE audit_log (
    id              UUID PRIMARY KEY,
    entity_type     VARCHAR(50) NOT NULL,
    entity_id       UUID NOT NULL,
    action_type     VARCHAR(100) NOT NULL,
    reasoning       TEXT NOT NULL,                 -- why this action was chosen
    actor           VARCHAR(20) NOT NULL,          -- 'agent' or 'human'
    npci_window     VARCHAR(50),                   -- which NPCI window was used
    attempt_number  INT,
    metadata        JSONB,                         -- additional context
    timestamp       TIMESTAMP DEFAULT NOW()
);

-- Dynamic configuration
CREATE TABLE policy_config (
    id              UUID PRIMARY KEY,
    root_cause      VARCHAR(100) NOT NULL,
    action_type     VARCHAR(100) NOT NULL,
    action_sequence JSONB,                         -- ordered list of actions
    max_attempts    INT NOT NULL,
    allowed_windows JSONB,                         -- NPCI time windows
    escalation_threshold INT,
    daily_cap       INT DEFAULT 2,
    is_active       BOOLEAN DEFAULT TRUE,
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Feature store for ML
CREATE TABLE customer_features (
    customer_id         VARCHAR(255) PRIMARY KEY,
    avg_transaction_amount DECIMAL(12,2),
    historical_success_rate DECIMAL(5,4),
    payment_frequency   VARCHAR(20),               -- weekly, monthly, etc.
    typical_payment_day INT,                        -- day of month
    on_time_payment_rate DECIMAL(5,4),             -- for B2B scoring
    total_transactions  INT DEFAULT 0,
    last_updated        TIMESTAMP DEFAULT NOW()
);
```

---

## 14. API Surface

### 14.1 Webhook Ingestion

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/webhooks/payment-event` | Ingest simulated Razorpay `payment.failed` and `subscription.charge.failed` events |
| `POST` | `/webhooks/invoice-overdue` | Ingest synthetic B2B overdue events |

### 14.2 Recovery Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/recovery/queue` | Current prioritized action queue (B2B sorted by expected recovery value) |
| `POST` | `/recovery/{id}/execute` | Trigger the next bounded action (simulated) |
| `GET` | `/recovery/{id}/status` | Status of a specific recovery case |

### 14.3 Diagnosis

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/diagnose` | Accepts transaction features, returns root cause + confidence |

### 14.4 Audit & Reporting

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/audit/{entity_type}/{entity_id}` | Full audit trail for one case |
| `GET` | `/audit/log` | Paginated audit log with filters |
| `GET` | `/reports/baseline-vs-agent` | The comparison numbers for the demo |
| `GET` | `/reports/summary` | Recovery summary (at-risk, recovered, rate, by root cause) |
| `GET` | `/reports/strategy-performance` | ROI per channel/strategy |
| `GET` | `/metrics` | Prometheus-compatible metrics endpoint |

### 14.5 Admin & Simulation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/policy/config` | Current policy configuration |
| `PUT` | `/policy/config/{root_cause}` | Update policy for a root cause |
| `POST` | `/simulate/generate-batch` | Generate synthetic test batch |
| `POST` | `/simulate/run-baseline` | Run naive baseline policy |
| `POST` | `/simulate/run-agent` | Run Nova agent policy |

---

## 15. Implementation Plan — Phase by Phase

### Phase 0 — Project Setup (Day 1, ~3 hours)

**Objective:** Get the development environment running.

- [ ] Initialize Git repo with `frontend/` and `backend/` folders
- [ ] Set up Docker Compose with PostgreSQL + Redis
- [ ] Create Python virtual environment and install core dependencies:
  ```
  fastapi, uvicorn, sqlalchemy, alembic, psycopg2-binary,
  celery, redis, scikit-learn, xgboost, pydantic, httpx
  ```
- [ ] Initialize Vite + React + TypeScript frontend
- [ ] Set up linting (ruff for Python, ESLint for TS)
- [ ] Create initial `README.md`
- [ ] Verify Docker Compose stack starts cleanly

**Deliverable:** Running dev environment with empty FastAPI app + React shell + PostgreSQL + Redis.

---

### Phase 1 — Data Model & Synthetic Data Generator (Day 1–2)

**Objective:** Build the data foundation.

- [ ] Create SQLAlchemy models for all tables (see Schema section)
- [ ] Set up Alembic for database migrations
- [ ] Run initial migration to create all tables
- [ ] Build synthetic data generator (`utils/synthetic_data.py`):
  - Generate **50+ realistic failed payment records** across all root-cause buckets
  - Generate **20+ overdue B2B invoices** with varying histories
  - Generate **10+ abandoned checkouts**
  - Include customer history records for ML features
- [ ] Write seed script to populate the database
- [ ] Verify data integrity with basic queries

**Deliverable:** PostgreSQL schema live, 80+ realistic test records generated covering all root-cause types.

---

### Phase 2 — Classification Layer (Day 2–3)

**Objective:** Build the root-cause diagnosis engine.

- [ ] Implement rule-based classifier (first pass):
  - Map Razorpay/bank error codes → root-cause buckets
  - Handle known codes with 100% confidence
- [ ] Build ML classifier (second pass, fallback):
  - Feature engineering: retry count, time since last attempt, amount vs. typical, historical success rate
  - Train XGBoost/gradient-boosted classifier on synthetic labeled data
  - Save trained model as `.pkl`
  - Implement confidence threshold (< 0.7 → generic retry + human flag)
- [ ] Build `/diagnose` API endpoint
- [ ] Log classification reasoning for every prediction
- [ ] Write unit tests for classifier

**Deliverable:** Root-cause buckets working on the synthetic batch; rules + fallback ML pipeline tested.

---

### Phase 3 — Policy Engine & NPCI Constraints (Day 3–4)

**Objective:** Build the decision engine with regulatory awareness.

- [ ] Implement NPCI validation module (`utils/npci.py`):
  - Time window checker (before 10 AM, 1–5 PM, after 9:30 PM)
  - Attempt counter & cap enforcer (max 4 total)
  - Next-valid-window scheduler
- [ ] Build policy engine (`services/policy_engine.py`):
  - Load policy config from database
  - Map root cause → action sequence
  - Check retry budget before each decision
  - Check NPCI window compliance
  - Output: recommended action with reasoning
- [ ] Seed `policy_config` table with default policies
- [ ] Write comprehensive unit tests for NPCI logic (edge cases!)

**Deliverable:** Decision table enforced in code; retry-window/attempt-cap logic tested with zero violations.

---

### Phase 4 — Execution Layer & Audit Trail (Day 4–5)

**Objective:** Build the action executor with full audit logging.

- [ ] Build action executor (`services/executor.py`):
  - Simulated adapters for: WhatsApp, Email (SendGrid), Voice (Twilio), SMS, Razorpay API retry
  - Each adapter logs the exact content that would be sent
- [ ] Build orchestrator (`services/orchestrator.py`):
  - Rate limiting (max 2 actions/customer/day)
  - Idempotency (using `transaction_id` as lock key in Redis)
  - Retry semantics for action-level failures
- [ ] Implement stopping rules (enforced in code, not just config):
  - Max 4 attempts per mandate
  - Max 1 checkout nudge
  - Max N invoice follow-ups before escalation
  - Customer opt-out support
- [ ] Build append-only audit logger:
  - Every action written to `audit_log` **before** execution
  - Includes reasoning, actor, timestamp, NPCI window used
- [ ] Build human escalation queue
- [ ] Write recovery API endpoints
- [ ] Write integration tests

**Deliverable:** Simulated dispatch working; append-only logging verified; stopping-rule & escalation logic tested.

---

### Phase 5 — B2B Ranking & Promise-to-Pay (Day 5)

**Objective:** Build the intelligent B2B collections prioritization.

- [ ] Build B2B scorer (`services/scorer.py`):
  - Train logistic regression on synthetic invoice features
  - Calculate `P(payment)` per invoice
  - Calculate expected recovery value: `amount × P(payment)`
  - Sort collections queue by expected value
- [ ] Build promise-to-pay tracker (`services/promise_tracker.py`):
  - State machine: `promised → due date passed → paid?`
  - Increment broken-promise counter on miss
  - Auto re-follow-up if under threshold
  - Escalate to human queue if over threshold
- [ ] Integrate B2B scoring into `/recovery/queue` endpoint
- [ ] Write unit tests for scorer and state machine

**Deliverable:** Expected-value scoring working; state machine tested; escalation on broken promises verified.

---

### Phase 6 — Dashboard & Baseline Comparison (Day 5–6)

**Objective:** Build the React dashboard that tells the story.

- [ ] Build API client (`services/api.ts`)
- [ ] Build dashboard pages:

  **Overview Page:**
  - Summary cards: Total At-Risk Revenue (₹), Total Recovered (₹), Recovery Rate (%)
  - Recovery rate gauge chart
  - Top root causes — donut chart
  - Trend line — recovery over time

  **Recovery Logs Page:**
  - Table: Time, Transaction ID, Root Cause, Action, Result, Audit Trail (expandable)
  - Clicking "Audit Trail" opens modal with full JSON log
  - Filters: date range, root cause, status, merchant

  **Baseline vs. Agent Comparison Page:**
  - Side-by-side metrics: total recovered, recovery rate by root cause
  - Retries wasted outside NPCI windows (baseline > 0, Nova = 0)
  - Average days-to-recovery for B2B invoices
  - Visual bar chart comparison

  **Strategy Performance Page:**
  - ROI per channel (WhatsApp, Email, Voice, Retry)
  - Success rate per recovery strategy
  - Helps merchants optimize their recovery mix

  **B2B Priority Queue Page:**
  - Invoices sorted by expected recovery value
  - Promise-to-pay status indicators
  - Escalation status

- [ ] Build baseline comparison runner
- [ ] Ensure responsive design
- [ ] Add loading states and error handling

**Deliverable:** Full React/TS dashboard showing recovered revenue, baseline-vs-agent delta, and audit viewer.

---

### Phase 7 — Polish, Testing & Demo Script (Day 6–7)

**Objective:** Make it demo-ready and bulletproof.

- [ ] Write unit tests for all services (model, decision engine, orchestrator)
- [ ] Write integration tests using pytest with test database
- [ ] Build the naive baseline policy (`utils/baseline.py`):
  - Retries every failure immediately, up to fixed count
  - Ignores NPCI windows
  - Chases invoices oldest-first
- [ ] Run full evaluation:
  - Generate fresh synthetic batch (50+ records)
  - Run baseline → capture results
  - Run Nova agent → capture results
  - Generate comparison report
- [ ] Polish UI: animations, loading states, error handling
- [ ] Prepare 5-minute demo script (see Demo Script section)
- [ ] Write final README with setup instructions
- [ ] Record backup demo video (optional but recommended)

**Deliverable:** Clean, tested, demo-ready product with honest before/after comparison.

---

## 16. Dashboard & UI Design

### 16.1 Overview Page
- **Summary Cards:** Total At-Risk Revenue (₹), Total Recovered (₹), Recovery Rate (%) — past 7 days
- **Recovery Rate Gauge:** Visual gauge chart showing percentage
- **Top 3 Root Causes:** Donut chart with distribution
- **Recovery Trend:** Line chart showing daily recovery over time

### 16.2 Recovery Logs
- **Table Columns:** Time, Transaction ID, Root Cause (with confidence), Action, Channel, Result, Audit Trail (button)
- **Audit Trail Modal:** Full JSON log showing detection → diagnosis → action → outcome
- **Filters:** Date range, root cause, status, merchant (if multi-tenant)

### 16.3 Baseline vs. Agent Comparison
- **Side-by-side bar charts:** Recovered revenue, recovery rate
- **Key metrics highlighted:**
  - Retries outside NPCI windows: Baseline = X, Nova = 0
  - Average days-to-recovery for B2B: Baseline vs. Nova
  - Revenue delta: +₹X,XXX more recovered
- **Honest failure reporting:** Cases where neither policy recovers

### 16.4 Strategy Performance
- **ROI per channel:** Bar chart (WhatsApp, Email, Voice, API Retry)
- **Success rate per cause:** Stacked chart
- **Recommendation engine:** "Increase WhatsApp budget — 2.3× ROI vs. 1.8× for voice"

### 16.5 B2B Priority Queue
- **Sorted by expected recovery value** (not date or amount)
- **Visual indicators:** Promise status, days overdue, escalation risk
- **One-click actions:** Send follow-up, mark promised, escalate

---

## 17. Evaluation Methodology

> This is what **proves** the project, not just describes it.

### 17.1 Process

1. Generate a synthetic batch of **50+ failed payments** and **overdue invoices** covering all root-cause buckets
2. Run **Baseline** (naive policy):
   - Retries every failure immediately, up to a fixed count
   - Ignores NPCI time windows
   - Chases invoices oldest-first
3. Run **Nova Agent** (constraint-aware policy) on the **identical batch**
4. Report side by side:

| Metric | Baseline | Nova | Delta |
|--------|----------|------|-------|
| Total revenue recovered (₹) | X | Y | +Z |
| Recovery rate (%) | A% | B% | +C% |
| Retries outside NPCI windows | N > 0 | **0** | -N |
| Average days-to-recovery (B2B) | D days | E days | -F days |
| Wasted retry attempts | W | **0** | -W |

5. **Report failures honestly** — cases where neither policy recovers the money, and why

### 17.2 Success Criteria

- Nova recovers **more revenue** than baseline on the same batch
- Nova wastes **zero retries** outside NPCI windows (baseline wastes some)
- Nova recovers B2B invoices **faster** (expected-value ranking vs. oldest-first)
- All actions are in the audit log with stated reasoning
- All stopping rules are enforced in code

---

## 18. Compliance & Ethics

### 18.1 Principles

- **Defense-only:** Nova only recovers revenue through legitimate, consented channels. It never manipulates users or uses deceptive tactics
- **Opt-out:** Every communication includes a clear opt-out mechanism (e.g., "Reply STOP to unsubscribe")
- **Bounded:** Hard limits on attempts and daily frequency to avoid harassment
- **Transparent:** Every action is logged and explainable — matches Razorpay's compliance bar
- **No overcharging:** No action can exceed the original transaction amount

### 18.2 Hard-Coded Safeguards

| Safeguard | Implementation |
|-----------|---------------|
| Attempt cap | `if attempts_used >= max_attempts: escalate()` — in code, not config |
| NPCI windows | `if not is_valid_npci_window(now()): schedule_next_window()` — in code |
| Daily cap | `if daily_actions >= 2: queue_for_tomorrow()` — in code |
| Opt-out | `if customer.opted_out: skip()` — checked before every action |
| Amount guard | `assert retry_amount <= original_amount` — in code |

---

## 19. Definition of Done

> Mapped directly to the track's evaluation bar.

- [ ] **Measured money recovered** across a batch of 50+ records, reported by root-cause bucket
- [ ] **Baseline vs. agent comparison** showing a real delta, not a single cherry-picked case
- [ ] **Every retry respects the 4-attempt cap** and the three NPCI time windows
- [ ] **Every money-adjacent action** is in the audit log with a stated reason before execution
- [ ] **Hard stopping rules enforced in code** (not just described) with human-escalation handoff
- [ ] **B2B queue sorted by expected recovery value**, not date or amount alone
- [ ] **Dashboard** showing all key metrics, audit trail, and comparison view
- [ ] **Honest failure reporting** — cases where recovery fails are documented, not hidden
- [ ] **Tests passing** — unit tests for classifier, policy engine, NPCI logic, orchestrator
- [ ] **Docker Compose** starts the full stack with one command

---

## 20. Demo Script

> 5-minute walkthrough for judging.

### Minute 1 — The Problem
Show the synthetic batch (50+ failed payments + overdue invoices, all root-cause types represented). Explain the three revenue leak points.

### Minute 2 — The Baseline (What Happens Today)
Run the naive baseline policy **live**. Highlight:
- Where it wastes retries outside NPCI windows
- Where it chases the wrong invoices first (oldest, not highest expected value)
- How many retries are burned on the wrong root cause

### Minute 3 — Nova in Action
Run Nova on the **identical batch**. Show:
- Root-cause classification with confidence scores
- Policy engine choosing different actions for different causes
- NPCI window compliance (zero violations)
- B2B queue reordered by expected recovery value

### Minute 4 — The Dashboard
Show the dashboard:
- Recovered revenue vs. baseline — the delta
- Recovery rate by root cause
- Retries-outside-window count: **0** for Nova
- Audit log for one full case end to end
- Strategy performance (ROI per channel)

### Minute 5 — Why Nova is Different
Close on the key differentiator:
- Every action was inside a **fixed, auditable, regulation-aware boundary**
- Not a generic LLM wrapper — a **deterministic, explainable recovery engine**
- Production-ready architecture that fits into Razorpay's Agent Studio
- Honest evaluation — failures are reported too

---

## 21. Final Pitch

**Nova is not a toy project.** It is a production-ready, commercially viable AI agent that:

- **Directly increases Razorpay's merchant revenue** — reducing churn and increasing transaction success
- **Fits perfectly into Razorpay's Agent Studio vision** — a pluggable, intelligent agent
- **Demonstrates full-stack engineering, ML, and product thinking** — exactly what Razorpay looks for
- **Has a clear, honest, and auditable metric bar** — no cherry-picking, just real results
- **Respects regulatory constraints** — NPCI compliance is hard-coded, not an afterthought

**With Nova, you don't just build a project — you build a business case.**

---

> **Ready to start coding. This blueprint is your single source of truth.**
>
> *Project Code Name: Nova (temporary — final name TBD)*

---

### Quick Start Commands

```bash
# Clone and enter the project
cd Nova

# Start infrastructure
docker-compose up -d postgres redis

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head
python -m app.utils.synthetic_data  # Generate test data
uvicorn app.main:app --reload --port 8000

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev

# Run evaluation
python -m app.utils.baseline      # Run naive baseline
python -m app.main --evaluate     # Run Nova agent + comparison report
```
