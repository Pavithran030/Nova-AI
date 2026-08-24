# Nova – Intelligent Revenue Recovery & Root‑Cause Analysis System

## 1. Project Overview

**Nova** is an AI‑driven revenue recovery agent that detects, diagnoses, and automatically recovers lost revenue from:
- Payment failures (declines, timeouts, 3DS issues)
- Checkout abandonment
- Failed subscription renewals
- Overdue B2B invoices

It shifts recovery from *passive, fixed‑interval retries* to **proactive, intelligent, and explainable actions**, directly increasing merchant revenue while maintaining full auditability.

This solution is built for **Track 03: AI Revenue Recovery** of the Razorpay hackathon, but is architected to integrate seamlessly into Razorpay’s **Agent Studio** ecosystem – making it a strategic asset for the company.

---

## 2. Problem Statement

Revenue leaks are multi‑step, often caused by a chain of events:

- A payment degrades → the gateway times out
- A checkout gets abandoned after the user adds items to the cart
- A subscription renewal fails due to expired card or insufficient balance
- An invoice goes overdue and the merchant has no automated chaser

Today, these are handled in silos with crude retry mechanisms and no root‑cause understanding. Merchants lose revenue without knowing *why* or *how* to fix it, and they lack a measurable, auditable recovery process.

**Nova closes the loop** – from detecting the problem, to diagnosing it, to choosing the right intervention, to recovering the money – all while logging every step for compliance.

---

## 3. Why This Track (Track 03)?

| Criterion | How Nova fits |
|-----------|---------------|
| **Direct business impact** | Recovery is measured in ₹ recovered – a metric merchants and Razorpay care about deeply. |
| **Razorpay’s strategic focus** | Agent Studio is the future; Nova is a perfect example of a revenue‑focused agent that can be published on the platform. |
| **Unique AI angle** | We don’t just retry – we **diagnose the root cause** and **adapt the recovery action** accordingly. |
| **Clear “Bar”** | The track requires *measured money recovered*, *bounded stopping rules*, and an *audit trail* – all built into Nova from day one. |

---

## 4. Unique Value Proposition

| Aspect | Traditional Approach | Nova |
|--------|----------------------|------|
| **Root Cause** | Not identified | Diagnosed from 100+ signals (gateway codes, user behavior, device, time, history) |
| **Recovery Action** | Fixed retries (e.g., 3 attempts every 24h) | Adaptive – based on root cause (e.g., 3DS timeout → re‑prompt; balance → retry on payday) |
| **Measurability** | Only attempts logged | ₹ recovered per strategy, ROI per action, success rate per cause |
| **Audit Trail** | Minimal or none | Full trace: detection → diagnosis → action → outcome, with stopping rules |
| **Compliance** | Often unbounded | Gated with max retries, daily caps, customer opt‑out, and escalation rules |

---

## 5. Core Features (Four Pillars)

### 5.1 Intelligent Root‑Cause Analysis

- **Input**: Transaction data (amount, gateway response code, user_id, device fingerprint, time of day, previous attempt count, subscription tenure, etc.)
- **Model**: Multi‑class classifier (XGBoost or Logistic Regression) trained on historical payment logs to predict the primary failure reason.
- **Output Classes** (examples):
  - `TIMEOUT` – 3DS / bank gateway timeout
  - `INSUFFICIENT_FUNDS` – balance low
  - `RISK_DECLINE` – flagged by fraud rules (potential false positive)
  - `NETWORK_ERROR` – transient network issue
  - `CARD_EXPIRED` – expired card on file
  - `ABANDONMENT` – cart not checked out
  - `OVERDUE` – invoice past due date

- **Confidence threshold**: If model confidence < 0.7, fallback to a generic retry with human‑in‑the‑loop flag.

### 5.2 Adaptive Recovery Workflow (Decision Engine)

- **Decision Engine**: Maps each root‑cause class to one or more recovery actions, with priority, timing, and conditions.
- **Examples of mapping**:

| Root Cause | Recovery Action |
|------------|-----------------|
| `TIMEOUT` | Send a WhatsApp / email / push notification with a one‑click retry link. |
| `INSUFFICIENT_FUNDS` | Wait until the user’s likely payday (learned from historical patterns) and retry, plus send a reminder 1 day before. |
| `RISK_DECLINE` | If confidence in false positive is high, auto‑appeal with evidence package (device, location, past good history). |
| `ABANDONMENT` | Generate a personalized discount coupon (e.g., 10% off) and send a reminder with the coupon. |
| `OVERDUE` | Trigger a Hinglish voice call (via Twilio) or WhatsApp message with a payment link and gentle reminder. |
| `CARD_EXPIRED` | Send an update‑card link via email/WhatsApp. |

- **Stopping rules** (bounded execution):
  - Max 3 retry attempts per transaction.
  - Max 2 actions per customer per day.
  - Customer can opt‑out globally via a single command (e.g., “STOP”).
  - Escalate to merchant dashboard if recovery fails after all attempts.

### 5.3 Verifiable Recovery Measurement

- Dashboard shows for each batch (e.g., last 7 days):
  - **Total at‑risk revenue** (sum of failed/abandoned amounts)
  - **Recovered revenue** (amount successfully recovered)
  - **Recovery rate** = Recovered / At‑risk × 100
  - **ROI per strategy** (e.g., WhatsApp recovery yields 2.3× ROI, voice yields 1.8×)
  - **Failure distribution** by root cause (helps merchants fix systemic issues)

- All metrics are computed on a held‑out test set, not cherry‑picked – honesty is baked in.

### 5.4 Compliant Audit Trail

- Every recovery attempt is logged with:
  - `timestamp`
  - `transaction_id`
  - `root_cause` (with model confidence)
  - `action_taken` (including exact content sent to user)
  - `channel` (WhatsApp, Email, SMS, Voice, API retry)
  - `result` (success, failed, stopped)
  - `stop_reason` (if stopped: max_attempts, opt_out, daily_cap, etc.)

- All logs stored in PostgreSQL, exposed via a read‑only API for merchant audit.
- Full transparency – no black‑box decisions.

---

## 6. Technical Architecture (High‑Level)
