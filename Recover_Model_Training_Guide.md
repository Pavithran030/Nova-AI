# Nova — Model Training & Development Guide

> **Project Code Name:** Nova (temporary — final name TBD)
>
> **Reference:** This guide is a companion to [NOVA_PROJECT_BLUEPRINT.md](file:///D:/Nova/NOVA_PROJECT_BLUEPRINT.md). All architecture, API, and directory references align with that master document.

This covers the two ML components inside Nova end to end: what data they need, how to generate it, how to train and evaluate each model, why these specific choices were made, and how they plug into the FastAPI backend.

---

## 0. The two models, at a glance

| | Model 1: Root-Cause Classifier | Model 2: Payment Probability Scorer |
|---|---|---|
| Type | Multi-class classification | Binary classification (probability output) |
| Algorithm | Gradient-boosted trees (XGBoost/LightGBM) or Random Forest | Logistic Regression |
| Input | Failed transaction features | Overdue invoice features |
| Output | One of **8 root-cause labels** | P(will be paid if chased now) |
| Feeds into | Policy engine's action decision (NPCI-aware) | B2B collections queue ranking (`amount × P(payment)`) |
| Confidence gate | If confidence < 0.7 → fallback to generic retry + human flag | N/A — probability is used directly |

Both are small, fast, tabular models — no GPU, no deep learning, and that's a deliberate choice explained in Section 5.

---

## 1. Model 1 — Root-Cause Classifier

### 1.1 Feature schema

| Feature | Type | Notes |
|---|---|---|
| `error_code` | categorical (one-hot or embedded) | from Razorpay/bank webhook payload |
| `retry_count` | integer | attempts used so far on this mandate (max 4 per NPCI rules) |
| `hours_since_last_attempt` | float | |
| `amount` | float | transaction amount (INR) |
| `amount_vs_customer_avg` | float | ratio to that customer's typical amount (from `customer_features` table) |
| `customer_historical_success_rate` | float | 0–1, from past N transactions (from `customer_features` table) |
| `hour_of_day` | integer (0–23) | for NPCI time-window pattern learning (valid: <10, 13–17, >21:30) |
| `day_of_month` | integer | insufficient-balance failures cluster near month-end |
| `mandate_age_days` | integer | older mandates more likely to be revoked/expired |
| `is_mandate` | boolean | whether this is a UPI Autopay mandate transaction |
| `device_fingerprint_hash` | integer | hashed device ID — helps detect fraud-decline false positives |
| `subscription_tenure_days` | integer | how long the customer has been subscribed |
| **Label** `root_cause` | categorical | `INSUFFICIENT_FUNDS`, `BANK_TIMEOUT`, `CARD_EXPIRED`, `MANDATE_REVOKED`, `RISK_DECLINE`, `NETWORK_ERROR`, `ABANDONMENT`, `OVERDUE` |

### 1.2 Synthetic data generator

Ground truth needs to be assigned by a rule with realistic noise — clean enough to be learnable, noisy enough to not be trivial.

```python
import numpy as np
import pandas as pd

def generate_transaction_batch(n=3000, seed=42):
    """Generate synthetic failed-transaction data covering all 8 root-cause classes.
    
    Aligns with Nova's root-cause taxonomy:
    INSUFFICIENT_FUNDS, BANK_TIMEOUT, CARD_EXPIRED, MANDATE_REVOKED,
    RISK_DECLINE, NETWORK_ERROR, ABANDONMENT, OVERDUE
    """
    rng = np.random.default_rng(seed)
    day_of_month = rng.integers(1, 29, n)
    hour_of_day = rng.integers(0, 24, n)
    retry_count = rng.integers(0, 4, n)  # max 4 per NPCI rules
    amount = rng.lognormal(mean=6.5, sigma=0.8, size=n)  # skewed, realistic INR amounts
    customer_avg = amount * rng.uniform(0.6, 1.4, n)
    success_rate = rng.beta(5, 2, n)  # most customers mostly succeed
    mandate_age = rng.integers(1, 400, n)
    is_mandate = rng.choice([0, 1], size=n, p=[0.4, 0.6])  # 60% are mandate txns
    device_hash = rng.integers(1000, 9999, n)
    subscription_tenure = rng.integers(0, 730, n)

    root_cause = []
    for i in range(n):
        r = rng.random()
        # month-end + low success rate → insufficient balance
        if day_of_month[i] > 24 and success_rate[i] < 0.6 and r < 0.75:
            root_cause.append("INSUFFICIENT_FUNDS")
        # old mandates → mandate revoked
        elif is_mandate[i] and mandate_age[i] > 365 and r < 0.6:
            root_cause.append("MANDATE_REVOKED")
        # unusual amount from new device → risk decline (false positive)
        elif amount[i] > customer_avg[i] * 1.5 and subscription_tenure[i] > 180 and r < 0.3:
            root_cause.append("RISK_DECLINE")
        # random network errors (~10%)
        elif r < 0.10:
            root_cause.append("NETWORK_ERROR")
        # bank timeouts (~12%)
        elif r < 0.22:
            root_cause.append("BANK_TIMEOUT")
        # expired card when amount exceeds typical
        elif amount[i] > customer_avg[i] * 1.3 and r < 0.4:
            root_cause.append("CARD_EXPIRED")
        # checkout abandonment (non-mandate transactions)
        elif not is_mandate[i] and r < 0.35:
            root_cause.append("ABANDONMENT")
        # B2B overdue
        elif r < 0.15:
            root_cause.append("OVERDUE")
        # fallback distribution
        else:
            root_cause.append(rng.choice(
                ["INSUFFICIENT_FUNDS", "BANK_TIMEOUT", "ABANDONMENT", "NETWORK_ERROR"],
                p=[0.35, 0.25, 0.25, 0.15]
            ))

    df = pd.DataFrame({
        "day_of_month": day_of_month,
        "hour_of_day": hour_of_day,
        "retry_count": retry_count,
        "amount": amount,
        "amount_vs_customer_avg": amount / customer_avg,
        "customer_historical_success_rate": success_rate,
        "mandate_age_days": mandate_age,
        "is_mandate": is_mandate,
        "device_fingerprint_hash": device_hash,
        "subscription_tenure_days": subscription_tenure,
        "root_cause": root_cause,
    })
    return df
```

Generate at least 3,000–5,000 synthetic rows — small enough to run instantly, large enough for the model to find real patterns across all 8 root-cause classes instead of memorizing noise. Verify class balance with `df['root_cause'].value_counts()` — if any class is below ~5%, consider adjusting generator probabilities or using `scale_pos_weight` in XGBoost.

### 1.3 Training script

```python
# File: backend/app/ml/train_classifier.py

import os
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay
import joblib

# Import from Nova's data generators
from app.utils.synthetic_data import generate_transaction_batch

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODEL_DIR, exist_ok=True)

def train_root_cause_classifier():
    """Train the root-cause classifier on synthetic data.
    
    Outputs:
      - root_cause_model.joblib
      - root_cause_label_encoder.joblib
      - confusion_matrix.png (for demo/dashboard)
      - feature_importance.png (for explainability evidence)
    """
    df = generate_transaction_batch(n=3000)
    X = df.drop(columns=["root_cause"])
    y = df["root_cause"]

    # Check class balance
    print("Class distribution:")
    print(y.value_counts())
    print()

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, stratify=y_enc, random_state=42
    )

    model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        objective="multi:softprob",
        eval_metric="mlogloss",
        use_label_encoder=False,
    )
    model.fit(X_train, y_train)

    # --- Evaluation ---
    preds = model.predict(X_test)
    print("\n=== Classification Report ===")
    print(classification_report(y_test, preds, target_names=le.classes_))

    # Confusion matrix (save for demo)
    cm = confusion_matrix(y_test, preds)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=le.classes_)
    fig, ax = plt.subplots(figsize=(10, 8))
    disp.plot(ax=ax, cmap="Blues", xticks_rotation=45)
    ax.set_title("Nova — Root-Cause Classifier: Confusion Matrix")
    plt.tight_layout()
    plt.savefig(os.path.join(MODEL_DIR, "confusion_matrix.png"), dpi=150)
    print(f"Saved confusion_matrix.png")

    # Feature importance (save for explainability demo)
    importances = model.feature_importances_
    sorted_idx = np.argsort(importances)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(range(len(sorted_idx)), importances[sorted_idx])
    ax.set_yticks(range(len(sorted_idx)))
    ax.set_yticklabels(X.columns[sorted_idx])
    ax.set_title("Nova — Root-Cause Classifier: Feature Importance")
    ax.set_xlabel("Importance")
    plt.tight_layout()
    plt.savefig(os.path.join(MODEL_DIR, "feature_importance.png"), dpi=150)
    print(f"Saved feature_importance.png")

    # Serialize
    joblib.dump(model, os.path.join(MODEL_DIR, "root_cause_model.joblib"))
    joblib.dump(le, os.path.join(MODEL_DIR, "root_cause_label_encoder.joblib"))
    print(f"\nModels saved to {MODEL_DIR}/")

    return model, le


if __name__ == "__main__":
    train_root_cause_classifier()
```

### 1.4 What to evaluate — and report in the demo

- **Per-class F1**, not just overall accuracy — with 8 root-cause classes, some will be rarer than others, and overall accuracy hides poor performance on those classes.
- **Confusion matrix** — show which root causes get confused with which. This is a stronger demo artifact than a single accuracy number because it shows you understand the model's failure modes, not just its win rate. Saved automatically as `confusion_matrix.png`.
- **Feature importance** (`model.feature_importances_`) — plotted and saved as `feature_importance.png`. This is your "explainability" evidence for the track's bar.
- **Confidence distribution** — histogram of `max(predict_proba)` per prediction. Verify that the 0.7 threshold meaningfully separates confident from uncertain predictions — if most predictions cluster above 0.9, the threshold is too low to be useful; if most are below 0.7, the model isn't learning enough signal.

### 1.5 Confidence Threshold & Fallback Logic

As specified in the [Nova Blueprint](file:///D:/Nova/NOVA_PROJECT_BLUEPRINT.md), if the classifier's confidence (max predicted probability) is **below 0.7**, Nova does NOT use the ML prediction. Instead:

1. The transaction is flagged with `confidence_below_threshold = True`
2. A **generic retry** action is applied (respecting NPCI window/cap constraints)
3. The case is added to the **human-in-the-loop review queue**
4. The audit log records: `"reasoning": "ML confidence below threshold (X.XX), applying generic retry with human review"`

This prevents the policy engine from making high-stakes decisions based on uncertain classifications.

---

## 2. Model 2 — B2B Payment Probability Scorer

### 2.1 Feature schema

| Feature | Type | Notes |
|---|---|---|
| `days_overdue` | integer | |
| `invoice_amount` | float | |
| `customer_ontime_rate` | float | historical, 0–1 |
| `prior_broken_promises` | integer | |
| `payment_history_length` | integer | number of past invoices with this customer |
| **Label** `paid` | binary | 1 = paid when chased, 0 = not paid |

### 2.2 Synthetic data generator

```python
def generate_invoice_batch(n=2000, seed=7):
    """Generate synthetic overdue-invoice data for B2B payment probability scoring.
    
    Features align with Nova's `invoices` and `customer_features` DB tables.
    The hidden logit rule creates a learnable but non-trivial relationship.
    """
    rng = np.random.default_rng(seed)
    days_overdue = rng.integers(1, 120, n)
    invoice_amount = rng.lognormal(mean=8, sigma=1.0, size=n)  # INR, realistic B2B amounts
    ontime_rate = rng.beta(4, 2, n)  # from customer_features.on_time_payment_rate
    broken_promises = rng.poisson(0.6, n)  # from invoices.broken_promise_count
    history_len = rng.integers(1, 40, n)  # from customer_features.total_transactions
    followup_count = rng.integers(0, 5, n)  # how many follow-ups already sent

    # hidden rule generating the true probability, then sample a binary outcome
    logit = (
        2.5 * ontime_rate
        - 0.015 * days_overdue
        - 0.6 * broken_promises
        + 0.01 * np.minimum(history_len, 20)
        - 0.1 * followup_count  # diminishing returns on follow-ups
        - 0.3
    )
    prob = 1 / (1 + np.exp(-logit))
    paid = rng.binomial(1, prob)

    return pd.DataFrame({
        "days_overdue": days_overdue,
        "invoice_amount": invoice_amount,
        "customer_ontime_rate": ontime_rate,
        "prior_broken_promises": broken_promises,
        "payment_history_length": history_len,
        "followup_count": followup_count,
        "paid": paid,
    })
```

### 2.3 Training script

```python
# File: backend/app/ml/train_scorer.py

import os
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.calibration import calibration_curve, CalibratedClassifierCV
import joblib

from app.utils.synthetic_data import generate_invoice_batch

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODEL_DIR, exist_ok=True)

def train_payment_scorer():
    """Train the B2B payment probability scorer.
    
    Outputs:
      - payment_probability_model.joblib
      - calibration_curve.png (for demo/dashboard)
      - coefficient_table printed (for explainability evidence)
    """
    df = generate_invoice_batch(n=2000)
    X = df.drop(columns=["paid"])
    y = df["paid"]

    print(f"Class balance: {y.value_counts().to_dict()}")
    print()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    scorer = LogisticRegression(max_iter=1000)
    scorer.fit(X_train, y_train)

    # --- Evaluation ---
    probs = scorer.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, probs)
    brier = brier_score_loss(y_test, probs)
    print(f"AUC: {auc:.4f}")
    print(f"Brier score (lower = better calibrated): {brier:.4f}")
    print()

    # Coefficients — direct interpretability evidence
    print("=== Coefficients (interpretability evidence) ===")
    for name, coef in zip(X.columns, scorer.coef_[0]):
        direction = "↑ payment odds" if coef > 0 else "↓ payment odds"
        print(f"  {name}: {coef:+.3f}  ({direction})")
    print(f"  intercept: {scorer.intercept_[0]:+.3f}")
    print()

    # Calibration curve (save for demo)
    prob_true, prob_pred = calibration_curve(y_test, probs, n_bins=10)
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(prob_pred, prob_true, marker="o", label="Nova Scorer")
    ax.plot([0, 1], [0, 1], "--", color="gray", label="Perfectly calibrated")
    ax.set_xlabel("Predicted probability")
    ax.set_ylabel("Observed frequency")
    ax.set_title(f"Nova — Payment Scorer: Calibration Curve\nAUC={auc:.3f}, Brier={brier:.4f}")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(MODEL_DIR, "calibration_curve.png"), dpi=150)
    print(f"Saved calibration_curve.png")

    # Check calibration quality — if poor, apply CalibratedClassifierCV
    if brier > 0.15:
        print("\n⚠️  Brier score > 0.15 — applying CalibratedClassifierCV...")
        calibrated = CalibratedClassifierCV(scorer, cv=5, method="sigmoid")
        calibrated.fit(X_train, y_train)
        new_brier = brier_score_loss(y_test, calibrated.predict_proba(X_test)[:, 1])
        print(f"  Calibrated Brier score: {new_brier:.4f}")
        if new_brier < brier:
            scorer = calibrated
            print("  Using calibrated model.")
        else:
            print("  Calibration did not improve — keeping original.")

    # Serialize
    joblib.dump(scorer, os.path.join(MODEL_DIR, "payment_probability_model.joblib"))
    print(f"\nModel saved to {MODEL_DIR}/")

    return scorer


if __name__ == "__main__":
    train_payment_scorer()
```

### 2.4 What to evaluate

- **AUC** — ranking quality (can it separate likely-payers from unlikely ones).
- **Brier score / calibration curve** — this matters more than AUC here, because you're multiplying the probability by amount for ranking. A model that's well-ranked but badly calibrated (e.g. everything predicted near 0.5–0.9) will distort the expected-value ranking.
- **Coefficients** — read straight off `scorer.coef_`. Each one is a directly interpretable statement ("each broken promise lowers payment odds by X") — this is your strongest interpretability evidence for the demo.

---

## 3. Integrating Both Models into the Nova FastAPI Backend

Both models are loaded once at application startup and exposed through the API endpoints defined in the [Nova Blueprint](file:///D:/Nova/NOVA_PROJECT_BLUEPRINT.md) (Section 14).

### 3.1 Model Loading Service

```python
# File: backend/app/services/classifier.py

import os
import joblib
import pandas as pd
from typing import Optional

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "ml", "models")
CONFIDENCE_THRESHOLD = 0.7  # Below this → generic retry + human flag

# Load once at import time (module-level singleton)
_root_cause_model = joblib.load(os.path.join(MODEL_DIR, "root_cause_model.joblib"))
_root_cause_encoder = joblib.load(os.path.join(MODEL_DIR, "root_cause_label_encoder.joblib"))

def classify_transaction(features: dict) -> dict:
    """Classify a failed transaction's root cause.
    
    Returns:
        dict with root_cause, confidence, and below_threshold flag.
        If confidence < 0.7, root_cause is set but flagged for human review.
    """
    X = pd.DataFrame([features])
    pred = _root_cause_model.predict(X)[0]
    proba = _root_cause_model.predict_proba(X)[0]
    confidence = float(max(proba))
    root_cause = _root_cause_encoder.inverse_transform([pred])[0]
    
    return {
        "root_cause": root_cause,
        "confidence": confidence,
        "below_threshold": confidence < CONFIDENCE_THRESHOLD,
        "all_probabilities": {
            label: float(p)
            for label, p in zip(_root_cause_encoder.classes_, proba)
        },
    }
```

### 3.2 Scoring Service

```python
# File: backend/app/services/scorer.py

import os
import joblib
import pandas as pd

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "ml", "models")

_payment_scorer = joblib.load(os.path.join(MODEL_DIR, "payment_probability_model.joblib"))

def score_invoice(features: dict) -> dict:
    """Score an overdue invoice's payment probability.
    
    Returns:
        dict with payment_probability and expected_recovery_value.
        expected_recovery_value = invoice_amount × P(payment)
    """
    X = pd.DataFrame([features])
    prob = float(_payment_scorer.predict_proba(X)[0][1])
    expected_value = prob * features["invoice_amount"]
    return {
        "payment_probability": prob,
        "expected_recovery_value": float(expected_value),
    }
```

### 3.3 API Endpoints

```python
# File: backend/app/api/webhooks.py (diagnosis endpoint)

from fastapi import APIRouter
from app.services.classifier import classify_transaction
from app.services.scorer import score_invoice

router = APIRouter()

@router.post("/diagnose")
def diagnose_transaction(features: dict):
    """POST /diagnose — accepts transaction features, returns root cause + confidence.
    
    Maps to Nova Blueprint Section 14.3.
    If confidence < 0.7, includes below_threshold=True for human review routing.
    """
    result = classify_transaction(features)
    
    # Log reasoning for audit trail
    reasoning = (
        f"Classified as {result['root_cause']} with confidence {result['confidence']:.3f}. "
    )
    if result["below_threshold"]:
        reasoning += "Below confidence threshold — routing to generic retry + human review."
    
    result["reasoning"] = reasoning
    return result


@router.post("/score/invoice")
def score_invoice_endpoint(features: dict):
    """POST /score/invoice — accepts invoice features, returns P(payment) + expected recovery value.
    
    Maps to Nova Blueprint Section 14.2 (recovery queue ranking).
    """
    return score_invoice(features)
```

Load both models once at startup (module-level, as above) — **never reload per request**. The policy engine calls `/diagnose` before deciding an action, and the collections queue calls `/score/invoice` to rank overdue invoices by expected recovery value.

---

## 4. Development Steps — Practical Order of Operations

> These steps map to **Phase 2 (Classification Layer)** and **Phase 5 (B2B Ranking)** in the [Nova Blueprint](file:///D:/Nova/NOVA_PROJECT_BLUEPRINT.md) (Section 15).

1. **Environment setup** — `pip install pandas numpy scikit-learn xgboost joblib matplotlib fastapi uvicorn`
2. **Write and sanity-check the two data generators** — print `.describe()` and `root_cause.value_counts()` / `paid.value_counts()` before trusting them. A generator with a 95/5 class split will need `class_weight` or stratified sampling adjustments. All 8 root-cause classes should appear.
3. **Train Model 1** (`python -m app.ml.train_classifier`), check per-class F1 and the confusion matrix. If one class is consistently confused with another (e.g. `NETWORK_ERROR` vs. `BANK_TIMEOUT`), that's a signal to add a feature that separates them.
4. **Train Model 2** (`python -m app.ml.train_scorer`), check AUC and calibration. If Brier score > 0.15, the script auto-applies `CalibratedClassifierCV`.
5. **Verify serialized models** — check that `backend/app/ml/models/` contains all `.joblib` files and `.png` evaluation artifacts.
6. **Wire up the FastAPI endpoints** (`/diagnose` and `/score/invoice`), test with `curl`/Postman:
   ```bash
   # Test root-cause classification
   curl -X POST http://localhost:8000/diagnose \
     -H "Content-Type: application/json" \
     -d '{"day_of_month": 27, "hour_of_day": 14, "retry_count": 2, "amount": 1500.0, "amount_vs_customer_avg": 1.1, "customer_historical_success_rate": 0.4, "mandate_age_days": 200, "is_mandate": 1, "device_fingerprint_hash": 5678, "subscription_tenure_days": 365}'

   # Test invoice scoring
   curl -X POST http://localhost:8000/score/invoice \
     -H "Content-Type: application/json" \
     -d '{"days_overdue": 15, "invoice_amount": 50000.0, "customer_ontime_rate": 0.85, "prior_broken_promises": 0, "payment_history_length": 12, "followup_count": 1}'
   ```
7. **Connect to the policy engine** (`services/policy_engine.py`) — classification output feeds the NPCI-aware action-decision table; scoring output feeds the B2B collections queue sorted by `expected_recovery_value`.
8. **Generate the evaluation artifacts for the demo**: confusion matrix plot, feature-importance bar chart, calibration curve, coefficient table. These are auto-saved by the training scripts into `backend/app/ml/models/`.
9. **Re-run the full baseline-vs-agent comparison** (from Blueprint Section 17) now that real model outputs are feeding the policy engine, not stubbed values.

### Directory Structure (aligned with Nova Blueprint)

```
Nova/
├── backend/
│   └── app/
│       ├── ml/
│       │   ├── train_classifier.py        # Train root-cause model (Model 1)
│       │   ├── train_scorer.py            # Train payment scorer (Model 2)
│       │   └── models/                    # Serialized models + evaluation artifacts
│       │       ├── root_cause_model.joblib
│       │       ├── root_cause_label_encoder.joblib
│       │       ├── payment_probability_model.joblib
│       │       ├── confusion_matrix.png
│       │       ├── feature_importance.png
│       │       └── calibration_curve.png
│       ├── services/
│       │   ├── classifier.py              # Root-cause classification service
│       │   ├── scorer.py                  # B2B payment probability service
│       │   └── policy_engine.py           # Decision engine (consumes both models)
│       ├── api/
│       │   ├── webhooks.py                # /diagnose endpoint
│       │   ├── recovery.py                # /score/invoice + /recovery/queue
│       │   └── reports.py                 # /reports/baseline-vs-agent
│       └── utils/
│           ├── synthetic_data.py          # Both generators (transactions + invoices)
│           └── baseline.py               # Naive baseline policy
```

---

## 5. Why This Model Set — The Advantages

**Gradient-boosted trees for root-cause classification (8 classes):**
- Handles mixed feature types (categorical error codes + numeric ratios + booleans like `is_mandate`) without heavy preprocessing.
- Trains in seconds on thousands of rows — no GPU, no long training loop to babysit during a hackathon.
- Gives feature importances for free, which is your explainability evidence for the track's bar.
- Handles class imbalance reasonably well with `scale_pos_weight`/class weighting if some root causes (e.g., `RISK_DECLINE`) are rarer than others.
- The confidence threshold (0.7) provides a natural fallback to human review — no overconfident black-box decisions.

**Logistic regression for payment probability:**
- Coefficients are directly interpretable — you can state, in plain language, exactly what drives the score up or down (e.g., "each broken promise lowers payment odds by X"). No black box to defend under judge questioning.
- Naturally well-calibrated (or easy to calibrate further with `CalibratedClassifierCV`, auto-applied if Brier > 0.15), which matters because the output probability is multiplied directly into a ranking — a miscalibrated score would silently produce a wrong-priority collections queue.
- Extremely cheap at inference time — fine for scoring an entire invoice batch on every dashboard refresh.

**Tabular ML over deep learning/LLM for both:**
- The problems are structured, low-dimensional, and tabular — a large model adds latency and opacity without an accuracy payoff.
- Small models are auditable end to end, which is the actual point of this track: judges are scoring "explainable, bounded" decision-making, not model size.
- Fast to retrain — if you find a data-generation bug the night before the demo, you can regenerate and retrain both models in under a minute.

**Keeping the LLM layer separate and downstream (Nova's architecture principle):**
- The money-affecting decision (which action to take) stays fully deterministic and traceable to a specific rule or model output — this is Nova's core design principle.
- The LLM, if added, only touches message wording (e.g., WhatsApp/Hinglish nudge copy) — never the decision — so a bad LLM output can't silently cause a compliance violation or an unbounded action.
- This separation is what allows Nova to claim: *"Every action was inside a fixed, auditable, regulation-aware boundary."*

---

## 6. Checklist — Training Component Done

> Maps to the "Definition of Done" in [Nova Blueprint Section 19](file:///D:/Nova/NOVA_PROJECT_BLUEPRINT.md).

- [ ] Both synthetic generators produce realistic, non-trivial class balance (all 8 root-cause classes present, none below ~5%)
- [ ] Root-cause classifier reports per-class F1 and a confusion matrix (saved as `confusion_matrix.png`), not just accuracy
- [ ] Payment scorer reports AUC **and** calibration (Brier score or calibration curve, saved as `calibration_curve.png`)
- [ ] Feature importances / coefficients are extracted and saved (as `feature_importance.png`) — ready to show in the demo
- [ ] Confidence threshold (0.7) tested — verify that below-threshold cases correctly route to generic retry + human flag
- [ ] Both models serialized to `backend/app/ml/models/` and loaded once at FastAPI startup, not per-request
- [ ] `/diagnose` and `/score/invoice` endpoints tested independently with `curl` before wiring into the policy engine
- [ ] Baseline-vs-agent comparison re-run with real (not stubbed) model outputs
- [ ] All evaluation artifacts (confusion matrix, feature importance, calibration curve) ready for dashboard display or pitch deck
