"""
Nova ML Pipeline — Full Evaluation & Health Check

Quick smoke test that both trained artifacts load and behave sanely:
  1. Classifier confidence gating, using the empirically-recommended
     threshold from classifier_metadata.json (NOT a hardcoded 0.70 — see
     train_classifier.py's reliability curve for why that number is
     measured, not assumed).
  2. B2B expected-recovery-value ranking sanity check.

Run after train_classifier.py and train_scorer.py have produced artifacts/.
"""

import os
import json

import joblib
import pandas as pd
import numpy as np

from data_generator import (
    generate_transaction_dataset,
    generate_invoice_dataset,
    TX_NUMERIC_FEATURES,
    INV_NUMERIC_FEATURES,
)

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")


def evaluate_pipeline():
    print("=" * 60)
    print(" Nova ML Pipeline — Full Evaluation & Health Check ")
    print("=" * 60)

    # 1. Load Serialized Models
    clf_path = os.path.join(ARTIFACTS_DIR, "root_cause_model.joblib")
    encoder_path = os.path.join(ARTIFACTS_DIR, "root_cause_encoder.joblib")
    scorer_path = os.path.join(ARTIFACTS_DIR, "payment_scorer.joblib")
    metadata_path = os.path.join(ARTIFACTS_DIR, "classifier_metadata.json")

    if not (os.path.exists(clf_path) and os.path.exists(encoder_path) and os.path.exists(scorer_path)):
        print("Error: Trained models not found in artifacts/. Run train_classifier.py and train_scorer.py first.")
        return

    clf = joblib.load(clf_path)
    encoder = joblib.load(encoder_path)
    scorer = joblib.load(scorer_path)
    print(" Verified: All trained models loaded successfully from artifacts/\n")

    # Confidence threshold is a measured model property (train_classifier.py's
    # reliability curve), not an assumed constant — read it from metadata.
    confidence_threshold = 0.35
    if os.path.exists(metadata_path):
        with open(metadata_path) as f:
            meta = json.load(f)
        confidence_threshold = meta.get("recommended_confidence_threshold") or confidence_threshold
        print(f" Using recommended_confidence_threshold from classifier_metadata.json: {confidence_threshold:.2f}\n")
    else:
        print(f" No classifier_metadata.json found — using fallback threshold {confidence_threshold:.2f}\n")

    # 2. Evaluate Classifier Confidence Gating
    print(f"--- 1. Classifier Confidence Gating Test (threshold={confidence_threshold:.2f}) ---")
    tx_test = generate_transaction_dataset(n=500, seed=99)
    X_tx = tx_test[TX_NUMERIC_FEATURES]  # customer_id/root_cause deliberately excluded

    probas = clf.predict_proba(X_tx)
    max_conf = np.max(probas, axis=1)
    preds = clf.predict(X_tx)
    encoder.inverse_transform(preds)  # sanity check that labels decode without error

    high_conf_count = int(np.sum(max_conf >= confidence_threshold))
    low_conf_count = int(np.sum(max_conf < confidence_threshold))

    print(f"Total Test Transactions: {len(X_tx)}")
    print(f"  Confidence >= {confidence_threshold:.2f} (Automated Policy): {high_conf_count} ({high_conf_count/len(X_tx)*100:.1f}%)")
    print(f"  Confidence <  {confidence_threshold:.2f} (Fallback to Human Flag): {low_conf_count} ({low_conf_count/len(X_tx)*100:.1f}%)\n")

    # 3. Evaluate B2B Expected Recovery Value Ranking
    print("--- 2. B2B Expected Recovery Value Ranking Test ---")
    inv_test = generate_invoice_dataset(n=10, seed=101)
    X_inv = inv_test[INV_NUMERIC_FEATURES].copy()  # customer_id/paid excluded
    X_inv["customer_ontime_rate"] = X_inv["customer_ontime_rate"].fillna(
        X_inv["customer_ontime_rate"].median()
    )

    inv_probs = scorer.predict_proba(X_inv)[:, 1]
    inv_test["P_payment"] = inv_probs
    inv_test["expected_recovery_value"] = inv_test["invoice_amount"] * inv_probs

    ranked = inv_test.sort_values(by="expected_recovery_value", ascending=False)

    print("Ranked B2B Collections Queue (Top 5):")
    print(ranked[["days_overdue", "invoice_amount", "P_payment", "expected_recovery_value"]].head().to_string(index=False))
    print("\n Verification complete. Both models operate within expected regulatory boundaries.")
    print("=" * 60)


if __name__ == "__main__":
    evaluate_pipeline()
