"""
Nova ML Pipeline — Model 2: B2B Payment Probability Scorer

Prerequisites:
    python data_generator.py     # writes data/*.csv
    python validate_dataset.py   # confirms the leakage/balance gate passes

Procedure implemented here (see TRAINING_GUIDE.md for the full walkthrough):
    1. Load pre-generated train/holdout CSVs
    2. Baseline sanity check (DummyClassifier)
    3. Regularization sweep on C, scored by validation Brier score
       (calibration matters more than raw accuracy for an EV-ranking scorer)
    4. Coefficient interpretability check (sign sanity)
    5. Optional CalibratedClassifierCV if Brier is still poor
    6. Final evaluation on the independent holdout batch
    7. Save model + calibration plot + metadata.json
"""

import os
import json
import datetime

import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.dummy import DummyClassifier
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.calibration import calibration_curve, CalibratedClassifierCV
import joblib

from data_generator import INV_NUMERIC_FEATURES, INV_LABEL_COLUMN

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)


def load_split():
    train_path = os.path.join(DATA_DIR, "invoices_train.csv")
    holdout_path = os.path.join(DATA_DIR, "invoices_holdout.csv")
    if not (os.path.exists(train_path) and os.path.exists(holdout_path)):
        raise FileNotFoundError(
            "data/*.csv not found. Run `python data_generator.py` first."
        )
    return pd.read_csv(train_path), pd.read_csv(holdout_path)


def _prep(df, fill_value):
    X = df[INV_NUMERIC_FEATURES].copy()
    X["customer_ontime_rate"] = X["customer_ontime_rate"].fillna(fill_value)
    return X


def train_scorer():
    print("=" * 60)
    print(" Nova ML Pipeline — Model 2: Payment Probability Scorer ")
    print("=" * 60)

    train_df, holdout_df = load_split()
    print(f"\n[1/7] Loaded {len(train_df)} train rows, {len(holdout_df)} holdout rows")
    print(train_df[INV_LABEL_COLUMN].value_counts().to_dict())

    ontime_median = train_df["customer_ontime_rate"].median()
    X = _prep(train_df, ontime_median)
    y = train_df[INV_LABEL_COLUMN]

    X_tr, X_val, y_tr, y_val = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    print("\n[2/7] Baseline (stratified random guesser)...")
    baseline = DummyClassifier(strategy="stratified", random_state=42)
    baseline.fit(X_tr, y_tr)
    baseline_brier = brier_score_loss(y_val, baseline.predict_proba(X_val)[:, 1])
    print(f"  Baseline Brier score: {baseline_brier:.4f}  (lower is better; beat this clearly)")

    print("\n[3/7] Regularization sweep on C, scored by validation Brier score...")
    best_C, best_brier, scorer = None, float("inf"), None
    for C in [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0]:
        candidate = LogisticRegression(C=C, max_iter=1000, random_state=42)
        candidate.fit(X_tr, y_tr)
        val_probs = candidate.predict_proba(X_val)[:, 1]
        train_probs = candidate.predict_proba(X_tr)[:, 1]
        val_brier = brier_score_loss(y_val, val_probs)
        train_brier = brier_score_loss(y_tr, train_probs)
        print(f"  C={C:<6} train Brier={train_brier:.4f}  val Brier={val_brier:.4f}")
        if val_brier < best_brier:
            best_C, best_brier, scorer = C, val_brier, candidate

    print(f"\n  Selected C={best_C} (val Brier={best_brier:.4f})")

    print("\n[4/7] Coefficient interpretability check...")
    for name, coef in zip(INV_NUMERIC_FEATURES, scorer.coef_[0]):
        direction = "up payment odds" if coef > 0 else "down payment odds"
        print(f"  {name:25s}: {coef:+.4f}  ({direction})")
    print(f"  {'intercept':25s}: {scorer.intercept_[0]:+.4f}")
    print("  Expected: customer_ontime_rate positive; days_overdue and")
    print("  prior_broken_promises negative. A flipped sign is a red flag.")

    val_probs = scorer.predict_proba(X_val)[:, 1]
    val_auc = roc_auc_score(y_val, val_probs)
    print(f"\n[5/7] Validation AUC = {val_auc:.4f} (ranking quality, secondary to Brier here)")

    if best_brier > 0.15:
        print("\n  Brier > 0.15 — applying CalibratedClassifierCV...")
        calibrated = CalibratedClassifierCV(scorer, cv=5, method="sigmoid")
        calibrated.fit(X_tr, y_tr)
        calibrated_brier = brier_score_loss(y_val, calibrated.predict_proba(X_val)[:, 1])
        print(f"  Calibrated val Brier: {calibrated_brier:.4f}")
        if calibrated_brier < best_brier:
            scorer = calibrated
            best_brier = calibrated_brier

    print("\n[6/7] Final evaluation on the independent holdout batch (different seed)...")
    X_hold = _prep(holdout_df, ontime_median)
    y_hold = holdout_df[INV_LABEL_COLUMN]
    hold_probs = scorer.predict_proba(X_hold)[:, 1]
    hold_brier = brier_score_loss(y_hold, hold_probs)
    hold_auc = roc_auc_score(y_hold, hold_probs)
    print(f"  Holdout Brier = {hold_brier:.4f} (val was {best_brier:.4f})")
    print(f"  Holdout AUC   = {hold_auc:.4f} (val was {val_auc:.4f})")
    if hold_brier - best_brier > 0.05:
        print("  WARNING: holdout Brier notably worse than val — check for tuning-to-val overfitting.")

    print("\n[7/7] Saving model, calibration plot, and metadata...")
    prob_true, prob_pred = calibration_curve(y_hold, hold_probs, n_bins=10)
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(prob_pred, prob_true, marker="o", color="#3B6CF5", label="Nova Scorer (holdout)")
    ax.plot([0, 1], [0, 1], "--", color="gray", label="Perfect calibration")
    ax.set_xlabel("Predicted P(payment)")
    ax.set_ylabel("Observed frequency")
    ax.set_title(f"Nova — Payment Scorer Calibration (holdout)\nAUC={hold_auc:.3f}, Brier={hold_brier:.4f}")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(ARTIFACTS_DIR, "calibration_curve.png"), dpi=150)
    plt.close()

    joblib.dump(scorer, os.path.join(ARTIFACTS_DIR, "payment_scorer.joblib"))

    metadata = {
        "trained_at": datetime.datetime.now().isoformat(),
        "model_type": type(scorer).__name__,
        "features": INV_NUMERIC_FEATURES,
        "selected_C": best_C,
        "n_train": int(len(X_tr)),
        "n_val": int(len(X_val)),
        "n_holdout": int(len(X_hold)),
        "baseline_brier": round(float(baseline_brier), 4),
        "val_brier": round(float(best_brier), 4),
        "val_auc": round(float(val_auc), 4),
        "holdout_brier": round(float(hold_brier), 4),
        "holdout_auc": round(float(hold_auc), 4),
    }
    with open(os.path.join(ARTIFACTS_DIR, "scorer_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"  Saved model, calibration_curve.png, and scorer_metadata.json to {ARTIFACTS_DIR}/")
    print("=" * 60)
    return scorer, metadata


if __name__ == "__main__":
    train_scorer()
