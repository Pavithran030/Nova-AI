# Nova — Intelligent Revenue Recovery Agent
### Track 03: AI Revenue Recovery — Razorpay Hackathon

**Nova** is an intelligent revenue recovery system that detects, classifies, and automatically recovers lost revenue from payment declines, checkout abandonment, failed subscriptions, and overdue B2B invoices while adhering strictly to NPCI Autopay retry constraints and maintaining an append-only audit log.

It diagnoses failures with a rules-first / ML-fallback classifier, decides the next action through a policy engine that enforces NPCI time windows and attempt caps **in code** (not just in prose), executes within a bounded action set, and proves its value by running an honest baseline-vs-agent comparison on the same batch.

---

## 📁 Repository Structure

```
Nova/
├── backend/                       # FastAPI + SQLite Backend
│   ├── app/
│   │   ├── api/                  # Endpoints: webhooks, recovery, reports, audit, simulate
│   │   ├── models/                # SQLAlchemy DB models
│   │   ├── schemas/                # Pydantic schemas
│   │   ├── services/              # Policy Engine, Classifier, Scorer, Orchestrator, Executor
│   │   ├── ml/                     # Trained-model loader + committed model artifacts
│   │   └── utils/                  # NPCI validator, synthetic data / history generators
│   ├── tests/                     # pytest: classifier, NPCI, policy engine, orchestrator
│   ├── requirements.txt
│   └── run.py                     # Uvicorn entrypoint
│
├── frontend/                       # Vite + React + TypeScript dashboard
│   └── src/
│       ├── pages/                  # Dashboard, Recovery Queue, Audit Trail, Comparison, Strategy
│       ├── services/api.ts         # Live API client (falls back to mock data if backend is down)
│       └── data/mockData.ts        # Fallback data, shaped identically to real API responses
│
├── ml_pipeline/                    # Standalone ML training pipeline (source of truth for models)
│   ├── data_generator.py           # Synthetic dataset generator
│   ├── validate_dataset.py         # Leakage / class-balance gate — run before training
│   ├── train_classifier.py         # XGBoost root-cause classifier
│   ├── train_scorer.py             # Logistic-regression B2B payment scorer
│   ├── evaluate.py / infer.py
│   └── TRAINING_GUIDE.md           # Full step-by-step training + diagnostics walkthrough
│
├── NOVA_PROJECT_BLUEPRINT.md        # Full architecture & design rationale
└── README.md
```

---

## 🚀 Quick Start (Local Development)

The repo ships with **already-trained model artifacts** in `backend/app/ml/models/` — you don't need to run `ml_pipeline/` before your first run. Retrain only if you want to (see `ml_pipeline/TRAINING_GUIDE.md`).

### 1. Backend (FastAPI)

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

# Optional but recommended: populate a realistic historical dataset
# (customers, mandates, transactions across every root-cause bucket,
# invoices, all run through the real decision pipeline) instead of
# starting from an empty database.
python -m app.utils.generate_history

# Verify the decision engine (NPCI enforcement, caps, classifier) end to end
pytest -v

python run.py
```
> API at `http://localhost:8000`, interactive docs at `http://localhost:8000/docs`.

### 2. Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```
> Dashboard at `http://localhost:5173`. Points at `http://localhost:8000` by default; override with a `VITE_API_URL` env var if needed. If the backend is unreachable, pages fall back to representative mock data rather than breaking.

---

## 🛠 Features

1. **Rules-first, ML-fallback root-cause classification** — known Razorpay/bank error codes map deterministically (`INSUFFICIENT_FUNDS`, `BANK_TIMEOUT`, `CARD_EXPIRED`, `MANDATE_REVOKED`, `RISK_DECLINE`, `NETWORK_ERROR`, `ABANDONMENT`, `OVERDUE`); ambiguous/unmapped cases fall back to a trained XGBoost classifier, with confidence-based human escalation using a threshold *measured* from validation data, not assumed.
2. **NPCI compliance enforced in code, not just logged** — mandate retries outside the allowed windows (before 10:00 AM, 1:00–5:00 PM, after 9:30 PM IST) are blocked and rescheduled for the agent policy; the 4-total-attempt cap is checked before every retry against real, incrementing counters.
3. **Hard stopping rules, all enforced in code** — daily action cap (2/customer/day), single checkout-nudge cap, invoice follow-up escalation threshold, and mandate attempt cap all stop automated action and record why, rather than continuing indefinitely.
4. **B2B expected-value prioritization** — a trained, calibrated logistic-regression scorer ranks overdue invoices by `amount × P(payment)`, not date or amount alone.
5. **Append-only audit trail, written before execution** — every action is logged with timestamp, actor (`agent`/`baseline`/`human`), reasoning, and NPCI-window status before it fires.
6. **Honest baseline-vs-agent comparison** — recovered revenue, recovery rate, real NPCI-window-violation counts, and average B2B days-to-recovery are computed from the same processed batch for both a naive baseline policy and Nova's policy, side by side.
7. **Live dashboard** — all five pages (Overview, Recovery Queue, Audit Trail, Comparison, Strategy) fetch real data from the backend.

---

## Testing

```bash
cd backend
pytest -v
```

Covers rule-based and ML-fallback classification, NPCI window logic, policy engine decisions, and orchestrator enforcement (attempt caps, daily caps, single-nudge cap, NPCI blocking, audit-before-execution) — all against an isolated in-memory database, never your real `nova.db`.

---

## Known limitations

- No Docker Compose / one-command startup — manual `pip install` + `npm install` setup only.
- Recovery outcomes are simulated (derived from root-cause recoverability, classifier confidence, NPCI compliance, and the real B2B scorer's `payment_probability` — not a live payment gateway).
- Three of the classifier's trained features (`card_age_days`, `network_quality_score`, `subscription_tenure_days`) have no live data source yet and use documented neutral defaults at inference time; the other 9 of 13 are real.
