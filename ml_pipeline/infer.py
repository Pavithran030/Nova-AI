"""
Nova ML Pipeline — Inference service sample runner.

Loads the trained artifacts and demonstrates a single prediction for each
model. Feature dicts are selected/reordered against TX_NUMERIC_FEATURES /
INV_NUMERIC_FEATURES from data_generator.py (the single schema source of
truth) rather than hardcoded column lists, so this can't silently drift out
of sync with what the models were actually trained on again.
"""

import os
import json

import joblib
import pandas as pd

from data_generator import TX_NUMERIC_FEATURES, INV_NUMERIC_FEATURES

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")


class NovaMLService:
    def __init__(self):
        clf_path = os.path.join(ARTIFACTS_DIR, "root_cause_model.joblib")
        encoder_path = os.path.join(ARTIFACTS_DIR, "root_cause_encoder.joblib")
        scorer_path = os.path.join(ARTIFACTS_DIR, "payment_scorer.joblib")
        metadata_path = os.path.join(ARTIFACTS_DIR, "classifier_metadata.json")

        if not (os.path.exists(clf_path) and os.path.exists(encoder_path) and os.path.exists(scorer_path)):
            raise FileNotFoundError("Trained models missing in artifacts/. Run train_classifier.py and train_scorer.py first.")

        self.clf = joblib.load(clf_path)
        self.encoder = joblib.load(encoder_path)
        self.scorer = joblib.load(scorer_path)

        # Confidence threshold is a measured model property, not an assumed
        # constant — pulled from the metadata train_classifier.py saved.
        self.confidence_threshold = 0.35
        if os.path.exists(metadata_path):
            with open(metadata_path) as f:
                meta = json.load(f)
            self.confidence_threshold = meta.get("recommended_confidence_threshold") or self.confidence_threshold

    def diagnose_transaction(self, sample: dict) -> dict:
        X = pd.DataFrame([sample])[TX_NUMERIC_FEATURES]
        pred_idx = self.clf.predict(X)[0]
        probas = self.clf.predict_proba(X)[0]
        confidence = float(max(probas))
        root_cause = self.encoder.inverse_transform([pred_idx])[0]

        below_threshold = confidence < self.confidence_threshold
        reasoning = f"Predicted {root_cause} with {confidence*100:.1f}% confidence."
        if below_threshold:
            reasoning += (
                f" Confidence below the {self.confidence_threshold:.2f} threshold. "
                "Escalating to human review & applying generic retry."
            )

        return {
            "root_cause": root_cause,
            "confidence": round(confidence, 4),
            "below_threshold": below_threshold,
            "reasoning": reasoning,
        }

    def score_invoice(self, sample: dict) -> dict:
        X = pd.DataFrame([sample])[INV_NUMERIC_FEATURES]
        prob = float(self.scorer.predict_proba(X)[0][1])
        expected_value = float(prob * sample["invoice_amount"])

        return {
            "payment_probability": round(prob, 4),
            "expected_recovery_value": round(expected_value, 2),
        }


if __name__ == "__main__":
    service = NovaMLService()

    # Sample transaction classification test — keys match TX_NUMERIC_FEATURES.
    sample_tx = {
        "day_of_month": 27,
        "hour_of_day": 14,
        "retry_count": 2,
        "is_mandate": 1,
        "mandate_age_days": 400,
        "card_age_days": 900,
        "subscription_tenure_days": 210,
        "customer_historical_success_rate": 0.45,
        "amount": 4500.0,
        "amount_vs_customer_avg": 1.2,
        "network_quality_score": 0.55,
        "device_is_new": 0,
        "has_error_description": 1,
    }
    tx_res = service.diagnose_transaction(sample_tx)
    print("Diagnosis Sample Output:")
    print(tx_res)

    # Sample invoice scoring test — keys match INV_NUMERIC_FEATURES.
    sample_inv = {
        "days_overdue": 18,
        "invoice_amount": 150000.0,
        "customer_ontime_rate": 0.85,
        "prior_broken_promises": 1,
        "payment_history_length": 15,
        "followup_count": 2,
    }
    inv_res = service.score_invoice(sample_inv)
    print("\nInvoice Scoring Sample Output:")
    print(inv_res)
