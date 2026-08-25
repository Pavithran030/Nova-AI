import os
import joblib
import pandas as pd

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")

class NovaMLService:
    def __init__(self):
        clf_path = os.path.join(ARTIFACTS_DIR, "root_cause_model.joblib")
        encoder_path = os.path.join(ARTIFACTS_DIR, "root_cause_encoder.joblib")
        scorer_path = os.path.join(ARTIFACTS_DIR, "payment_scorer.joblib")

        if not (os.path.exists(clf_path) and os.path.exists(encoder_path) and os.path.exists(scorer_path)):
            raise FileNotFoundError("Trained models missing in artifacts/. Run train_classifier.py and train_scorer.py first.")

        self.clf = joblib.load(clf_path)
        self.encoder = joblib.load(encoder_path)
        self.scorer = joblib.load(scorer_path)
        self.confidence_threshold = 0.70

    def diagnose_transaction(self, sample: dict) -> dict:
        X = pd.DataFrame([sample])
        pred_idx = self.clf.predict(X)[0]
        probas = self.clf.predict_proba(X)[0]
        confidence = float(max(probas))
        root_cause = self.encoder.inverse_transform([pred_idx])[0]

        below_threshold = confidence < self.confidence_threshold
        reasoning = f"Predicted {root_cause} with {confidence*100:.1f}% confidence."
        if below_threshold:
            reasoning += " Confidence below 70% threshold. Escalating to human review & applying generic retry."

        return {
            "root_cause": root_cause,
            "confidence": round(confidence, 4),
            "below_threshold": below_threshold,
            "reasoning": reasoning
        }

    def score_invoice(self, sample: dict) -> dict:
        X = pd.DataFrame([sample])
        prob = float(self.scorer.predict_proba(X)[0][1])
        expected_value = float(prob * sample["invoice_amount"])

        return {
            "payment_probability": round(prob, 4),
            "expected_recovery_value": round(expected_value, 2)
        }

if __name__ == "__main__":
    service = NovaMLService()

    # Sample transaction classification test
    sample_tx = {
        "day_of_month": 27,
        "hour_of_day": 14,
        "retry_count": 2,
        "amount": 4500.0,
        "amount_vs_customer_avg": 1.2,
        "customer_historical_success_rate": 0.45,
        "mandate_age_days": 180,
        "is_mandate": 1,
        "device_fingerprint_hash": 5432,
        "subscription_tenure_days": 210
    }
    tx_res = service.diagnose_transaction(sample_tx)
    print("Diagnosis Sample Output:")
    print(tx_res)

    # Sample invoice scoring test
    sample_inv = {
        "days_overdue": 18,
        "invoice_amount": 150000.0,
        "customer_ontime_rate": 0.85,
        "prior_broken_promises": 1,
        "payment_history_length": 15,
        "followup_count": 2
    }
    inv_res = service.score_invoice(sample_inv)
    print("\nInvoice Scoring Sample Output:")
    print(inv_res)
