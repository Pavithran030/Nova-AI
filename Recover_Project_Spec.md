# Recover — AI-Powered Revenue Recovery Agent
### Track 03: AI Revenue Recovery — Razorpay Hackathon

---

## 1. Problem Statement

Indian merchants lose recurring and B2B revenue at three points that are almost always handled by three disconnected, naive scripts instead of one coherent system:

1. **UPI Autopay failures.** UPI Autopay mandates fail roughly 8–15% of the time, several times the 2–3% failure rate of card mandates — mostly from insufficient balance, bank server timeouts, or expired mandates. Since NPCI's August 2025 rule change, every mandate is capped at **4 total attempts (1 original + 3 retries)** and autopay execution is restricted to specific windows (before 10:00 AM, 1:00–5:00 PM, after 9:30 PM). A merchant that retries blindly, outside these windows or without regard to root cause, burns its entire retry budget on the wrong problem and permanently loses that cycle's payment.
2. **Checkout payment failures.** When a payment fails mid-checkout, most customers simply abandon rather than retry. There is rarely an automated recovery flow — just a lost sale.
3. **B2B receivables.** Overdue invoices get chased manually over email/WhatsApp/calls, usually sorted by "oldest first" or "largest first" — not by which invoices are actually likely to be paid if chased now.

Each of these is usually solved (if at all) by a separate point tool. None of them reason about the other two, none of them respect the regulatory retry constraints that actually govern UPI, and none of them report an honest, measured before/after recovery number.

## 2. Solution Overview

**Recover** is a single agent that owns the full revenue-recovery lifecycle across all three leak points instead of one narrow slice of it:

- **Classifies** why a payment or invoice is at risk (root-cause bucket, not just "failed").
- **Decides** the recovery action using a policy engine that is aware of NPCI's actual retry-window and attempt-count constraints — never "just retry again."
- **Executes** within a bounded, fully audited action set — nothing open-ended, nothing that can silently overcharge or spam a customer.
- **Prioritizes** B2B collections by expected recovery value (`amount × probability of payment`) rather than naive sort order.
- **Proves its value** by running a naive "retry everything, chase in date order" baseline against its own policy on the same synthetic batch, and reporting the recovered-revenue delta — not a cherry-picked success story.

This directly satisfies the track's stated bar: *"Don't just identify the problem. Show measured money recovered across a batch, with compliant escalation, stopping rules, and an audit trail."*

## 3. End-to-End Workflow

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

**Step by step:**

1. **Ingest** — A Razorpay test-mode webhook simulator emits `payment.failed`, `subscription.charged.failed`, and synthetic `invoice.overdue` events into a queue.
2. **Classify** — Each event is bucketed into a root cause: insufficient balance, bank timeout, expired card, mandate expired/revoked, or (for invoices) days-overdue with payment-history context.
3. **Decide** — The policy engine looks up the root-cause bucket, checks remaining retry budget and the current time against NPCI's allowed windows, and picks the next action from a fixed action set.
4. **Execute** — The chosen action runs (simulated SMS/WhatsApp/email dispatch, mandate re-auth link, a scheduled smart retry, or an invoice follow-up), and every action is written to the audit log before it fires.
5. **Stop or escalate** — If retry/contact caps are hit, or a "promise to pay" is broken past its threshold, the case moves to a human-review queue instead of continuing automatically.

## 4. Methodology

### 4.1 Root-cause classification

Keep this interpretable — it's the piece judges will probe hardest on "explainability."

- **First pass (rules):** map Razorpay/bank error codes directly to buckets (e.g. `INSUFFICIENT_FUNDS`, `BANK_TIMEOUT`, `CARD_EXPIRED`, `MANDATE_REVOKED`).
- **Second pass (lightweight ML):** for ambiguous or unmapped codes, a small gradient-boosted classifier using features like: retry count so far, time since last attempt, transaction amount vs typical amount for that customer, and historical success rate for that customer/mandate.
- Log the *reason* for every classification, not just the label — this is what makes the decision auditable later.

### 4.2 Recovery action policy table

| Root cause | Recovery action | Constraint applied |
|---|---|---|
| Insufficient balance | Delay retry to a likely salary-credit date (1st/7th of month) within an allowed NPCI window | Max 3 retries, must land in 10am/1–5pm/9:30pm+ windows |
| Bank timeout | Immediate retry with short backoff | Counts against the same 4-attempt cap |
| Expired/near-expiry card | Send update-payment-method link, no auto-retry | No mandate retry attempted |
| Mandate revoked/expired | Trigger re-authorization flow | One re-auth request only, then escalate |
| Checkout abandonment | Time-boxed reminder (single nudge) with resume-checkout link | One nudge only — no repeated contact |
| Overdue B2B invoice | Rank by `amount × P(payment)`, auto-send templated follow-up, track promise-to-pay | Escalate to human after N broken promises |

### 4.3 B2B expected-recovery-value ranking

Train a simple logistic regression (or even a hand-tuned scoring formula for the hackathon) on synthetic invoice history features: days overdue, invoice size, customer's historical on-time-payment rate, and count of prior broken promises. Output `P(payment)` per invoice, multiply by `amount`, and sort the collections queue by that expected value — not by due date or invoice size alone. This single change is the clearest "we thought about this more than a to-do list" signal in the whole build.

### 4.4 Promise-to-pay tracker

A small state machine per invoice: `promised → due date passed → paid?` If not paid, increment a broken-promise counter and re-follow-up; once the counter crosses a configured threshold, stop automated contact and hand off to the human queue. This is the "compliant escalation" the track's bar explicitly asks for.

### 4.5 Bounded actions & audit trail

- Every money-adjacent action (retry attempt, re-auth request, contact sent) is written to an **append-only** `audit_log` table before execution — action type, reasoning, timestamp, actor (`agent` vs `human`).
- Hard caps are enforced in code, not just policy: max 4 total attempts per mandate, max 1 checkout nudge, max N invoice follow-ups before mandatory escalation.
- No action can exceed the original transaction amount, and no action fires outside the allowed NPCI time windows.

### 4.6 Evaluation methodology (this is what proves the project, not just describes it)

1. Generate a synthetic batch of 50+ failed payments/overdue invoices covering all root-cause buckets.
2. Run **Baseline**: a naive policy that retries every failure immediately, up to some fixed count, and chases invoices oldest-first.
3. Run **Recover**: the constraint-aware policy on the identical batch.
4. Report, side by side: total revenue recovered, recovery rate by root-cause bucket, retries wasted outside valid windows (baseline should show non-zero, Recover should show zero), and average days-to-recovery for B2B invoices.
5. Report failures honestly too — cases where neither policy recovers the money, and why.

## 5. Development Plan

### 5.1 Tech stack

- **Backend:** FastAPI (Python) — webhook ingestion, classification service, policy engine, execution simulator, reporting API.
- **Database:** PostgreSQL — transactional state, audit log, policy config.
- **Frontend:** React + Vite + TypeScript — recovery dashboard, audit log viewer, baseline-vs-agent comparison view.
- **ML pieces:** scikit-learn (gradient boosting for root-cause classification, logistic regression for B2B scoring) — no need for anything heavier; interpretability matters more than raw model power here.
- **Optional LLM layer:** used only inside the fixed action set (e.g. drafting the *wording* of a WhatsApp/Hinglish nudge for a chosen action) — never used to choose the action itself. Keeps the money-decision path fully deterministic and explainable.

### 5.2 Core database schema (sketch)

```sql
merchants(id, name, tenant_id, created_at)

transactions(id, merchant_id, amount, status, error_code,
             mandate_id, attempt_count, last_attempt_at, created_at)

mandates(id, merchant_id, customer_id, status, expiry_date,
         max_attempts, attempts_used)

invoices(id, merchant_id, customer_id, amount, due_date,
         status, days_overdue, broken_promise_count)

recovery_actions(id, entity_type, entity_id, root_cause,
                  action_type, decided_at, executed_at, outcome)

audit_log(id, entity_type, entity_id, action_type, reasoning,
          actor, timestamp)   -- append-only, never updated or deleted

policy_config(id, root_cause, action_type, max_attempts,
              allowed_windows, escalation_threshold)
```

### 5.3 API surface (sketch)

- `POST /webhooks/payment-event` — ingest simulated Razorpay events
- `POST /webhooks/invoice-overdue` — ingest synthetic B2B overdue events
- `GET /recovery/queue` — current prioritized action queue
- `POST /recovery/{id}/execute` — trigger the next bounded action (simulated)
- `GET /audit/{entity_type}/{entity_id}` — full audit trail for one case
- `GET /reports/baseline-vs-agent` — the comparison numbers for the demo

### 5.4 Build phases

| Phase | Focus | Deliverable |
|---|---|---|
| 1 | Data model + synthetic data generator | Postgres schema live, 50+ realistic failed-payment/invoice records generated |
| 2 | Classification layer | Root-cause buckets working on the synthetic batch, rules + fallback ML |
| 3 | Policy engine + NPCI constraints | Decision table enforced in code, retry-window/attempt-cap logic tested |
| 4 | Execution + audit trail | Simulated dispatch, append-only logging, stopping-rule/escalation logic |
| 5 | B2B ranking + promise-to-pay | Expected-value scoring, state machine, escalation on broken promises |
| 6 | Dashboard + baseline comparison | React/TS UI showing recovered revenue, baseline-vs-agent delta, audit viewer |
| 7 | Polish + demo script | Clean run-through: seed batch → baseline run → agent run → dashboard reveal |

### 5.5 Definition of done (mapped to the track's bar)

- [ ] Measured money recovered across a batch of 50+ records, reported by root-cause bucket
- [ ] Baseline vs agent comparison showing a real delta, not a single cherry-picked case
- [ ] Every retry respects the 4-attempt cap and the three NPCI time windows
- [ ] Every money-adjacent action is in the audit log with a stated reason before execution
- [ ] Hard stopping rules enforced in code (not just described) with human-escalation handoff
- [ ] B2B queue sorted by expected recovery value, not date or amount alone

## 6. Demo Script (for judging)

1. Show the synthetic batch (50+ failed payments + overdue invoices, all root-cause types represented).
2. Run the naive baseline policy live — highlight where it wastes retries outside NPCI windows or chases the wrong invoices first.
3. Run Recover on the identical batch.
4. Show the dashboard: recovered revenue, delta over baseline, retries-outside-window count (zero for Recover), audit log for one full case end to end.
5. Close on the one thing a generic LLM wrapper can't claim: every action taken was inside a fixed, auditable, regulation-aware boundary.

---

*Note: NPCI retry-cap and time-window figures reflect the August 2025 rule change as reported publicly. Verify current figures against official NPCI/Razorpay documentation before treating them as production-accurate.*
