# Nova — Intelligent Revenue Recovery Agent
### Track 03: AI Revenue Recovery — Razorpay Hackathon

**Nova** is an intelligent revenue recovery system that detects, classifies, and automatically recovers lost revenue from payment declines, checkout abandonment, failed subscriptions, and overdue B2B invoices while adhering strictly to NPCI Autopay retry constraints and maintaining an append-only audit log.

---

## 📁 Repository Structure

```
Nova/
├── backend/                  # FastAPI + SQLite Backend
│   ├── app/
│   │   ├── api/             # API Endpoints (webhooks, recovery, reports, audit, simulate)
│   │   ├── models/          # SQLAlchemy Database Models
│   │   ├── schemas/         # Pydantic Schemas
│   │   ├── services/        # Policy Engine, Classifier, Scorer, Orchestrator, Executor
│   │   └── utils/           # NPCI Validator, Synthetic Data Generator, Baseline Policy
│   ├── requirements.txt     # Python Dependencies
│   └── run.py               # Uvicorn Local Server Entrypoint
│
├── frontend/                 # Vite + React + TypeScript Dashboard (Fintech SaaS UI)
│   ├── src/
│   │   ├── components/      # Reusable UI Elements (Sidebar, MetricCard, DataTable, StatusBadge)
│   │   ├── pages/           # Dashboard, Recovery Queue, Audit Trail, Comparison, Strategy
│   │   ├── services/        # API Integration / Mock Client
│   │   └── data/            # Mock Dataset for standalone UI testing
│   └── package.json         # Node Dependencies
│
├── NOVA_PROJECT_BLUEPRINT.md  # Detailed Project Architecture & Blueprint
├── Recover_Model_Training_Guide.md # Companion ML Architecture & Guidance
└── README.md                 # Project README
```

---

## 🚀 Quick Start Guide (Local Development)

### 1. Backend Setup (FastAPI)

```bash
# Navigate to backend directory
cd backend

# Create & activate a virtual environment (optional but recommended)
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the API server
python run.py
```
> The backend server will run at `http://localhost:8000`. You can inspect the Swagger API docs at `http://localhost:8000/docs`.

### 2. Frontend Setup (React + Vite)

```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start local dev server
npm run dev
```
> The frontend application will run at `http://localhost:5173`.

---

## 🛠 Features

1. **Intelligent Root-Cause Analysis**: Categorizes failed payments into `INSUFFICIENT_FUNDS`, `BANK_TIMEOUT`, `CARD_EXPIRED`, `MANDATE_REVOKED`, `RISK_DECLINE`, `NETWORK_ERROR`, `ABANDONMENT`, and `OVERDUE`.
2. **NPCI Regulation Compliance**: Hard-coded constraints respecting maximum retry caps (4 total) and allowed execution windows (before 10:00 AM, 1:00 PM – 5:00 PM, after 9:30 PM IST).
3. **B2B Expected-Value Prioritization**: Ranks overdue invoices by `amount × P(payment)` instead of naive date sorting.
4. **Append-Only Audit Trail**: Full auditable ledger recording timestamp, actor (`agent` vs `human`), reasoning, and execution outcome for compliance.
5. **Honest Baseline Comparison**: Evaluates Nova side-by-side against a naive baseline policy to measure true recovery uplift.
