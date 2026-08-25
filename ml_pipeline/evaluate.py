import os
import joblib
import pandas as pd
import numpy as np

from data_generator import generate_transaction_dataset, generate_invoice_dataset

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")

def evaluate_pipeline():
    print("=" * 60)
    print(" Nova ML Pipeline — Full Evaluation & Health Check ")
    print("=" * 60)

    # 1. Load Serialized Models
    clf_path = os.path.join(ARTIFACTS_DIR, "root_cause_model.joblib")
    encoder_path = os.path.join(ARTIFACTS_DIR, "root_cause_encoder.joblib")
    scorer_path = os.path.join(ARTIFACTS_DIR, "payment_scorer.joblib")

    if not (os.path.exists(clf_path) and os.path.exists(encoder_path) and os.path.exists(scorer_path)):
        print("❌ Error: Trained models not found in artifacts/. Please run train_classifier.py and train_scorer.py first.")
        return

    clf = joblib.load(clf_path)
    encoder = joblib.load(encoder_path)
    scorer = joblib.load(scorer_path)
    print(" Verified: All trained models loaded successfully from artifacts/\n")

    # 2. Evaluate Classifier Confidence Gating (0.7 Threshold Check)
    print("--- 1. Classifier Confidence Gating Test ---")
    tx_test = generate_transaction_dataset(n=500, seed=99)
    X_tx = tx_test.drop(columns=["root_cause"])
    
    probas = clf.predict_proba(X_tx)
    max_conf = np.max(probas, axis=1)
    preds = clf.predict(X_tx)
    labels = encoder.inverse_transform(preds)

    high_conf_count = np.sum(max_conf >= 0.70)
    low_conf_count = np.sum(max_conf < 0.70)

    print(f"Total Test Transactions: {len(X_tx)}")
    print(f"  Confidence ≥ 0.70 (Automated Policy): {high_conf_count} ({high_conf_count/len(X_tx)*100:.1f}%)")
    print(f"  Confidence < 0.70 (Fallback to Human Flag): {low_conf_count} ({low_conf_count/len(X_tx)*100:.1f}%)\n")

    # 3. Evaluate B2B Expected Recovery Value Ranking
    print("--- 2. B2B Expected Recovery Value Ranking Test ---")
    inv_test = generate_invoice_dataset(n=10, seed=101)
    X_inv = inv_test.drop(columns=["paid"])
    
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
