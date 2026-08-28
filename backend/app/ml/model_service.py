"""
Nova Backend — trained-model loader.

Loads the artifacts produced by ml_pipeline/train_classifier.py and
train_scorer.py exactly once at import time (singleton `model_service`
instance below), so requests don't pay model-load cost per call.

Feature order/names here MUST match ml_pipeline/data_generator.py's
TX_NUMERIC_FEATURES / INV_NUMERIC_FEATURES exactly — they're duplicated
(not imported) because the backend and ml_pipeline are separate
requirements.txt / deployment units; if you change the training schema,
update both.

If artifacts are missing, `classifier_available` / `scorer_available` are
False and ML-backed methods raise — callers (app/services/classifier.py,
app/services/scorer.py) must check availability and fall back to the
rule-based / hand-tuned logic rather than let the backend crash.
"""

import os
import json

import joblib
import pandas as pd

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

TX_NUMERIC_FEATURES = [
    "day_of_month",
    "hour_of_day",
    "retry_count",
    "is_mandate",
    "mandate_age_days",
    "card_age_days",
    "subscription_tenure_days",
    "customer_historical_success_rate",
    "amount",
    "amount_vs_customer_avg",
    "network_quality_score",
    "device_is_new",
    "has_error_description",
]
INV_NUMERIC_FEATURES = [
    "days_overdue",
    "invoice_amount",
    "customer_ontime_rate",
    "prior_broken_promises",
    "payment_history_length",
    "followup_count",
]
DEFAULT_CONFIDENCE_THRESHOLD = 0.35  # only used if classifier_metadata.json is missing


class ModelService:
    def __init__(self):
        self.classifier = None
        self.encoder = None
        self.scorer = None
        self.confidence_threshold = DEFAULT_CONFIDENCE_THRESHOLD
        self._load()

    def _load(self):
        clf_path = os.path.join(MODELS_DIR, "root_cause_model.joblib")
        enc_path = os.path.join(MODELS_DIR, "root_cause_encoder.joblib")
        scorer_path = os.path.join(MODELS_DIR, "payment_scorer.joblib")
        meta_path = os.path.join(MODELS_DIR, "classifier_metadata.json")

        if os.path.exists(clf_path) and os.path.exists(enc_path):
            self.classifier = joblib.load(clf_path)
            self.encoder = joblib.load(enc_path)

        if os.path.exists(scorer_path):
            self.scorer = joblib.load(scorer_path)

        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
            self.confidence_threshold = (
                meta.get("recommended_confidence_threshold") or DEFAULT_CONFIDENCE_THRESHOLD
            )

    @property
    def classifier_available(self) -> bool:
        return self.classifier is not None and self.encoder is not None

    @property
    def scorer_available(self) -> bool:
        return self.scorer is not None

    def predict_root_cause(self, features: dict):
        """features must contain every key in TX_NUMERIC_FEATURES.
        Returns (root_cause: str, confidence: float, below_threshold: bool)."""
        if not self.classifier_available:
            raise RuntimeError(
                "Root-cause classifier not loaded. Run ml_pipeline training "
                "and copy artifacts into backend/app/ml/models/."
            )
        X = pd.DataFrame([features])[TX_NUMERIC_FEATURES]
        pred_idx = self.classifier.predict(X)[0]
        proba = self.classifier.predict_proba(X)[0]
        confidence = float(max(proba))
        root_cause = str(self.encoder.inverse_transform([pred_idx])[0])
        return root_cause, confidence, confidence < self.confidence_threshold

    def predict_payment_probability(self, features: dict) -> float:
        """features must contain every key in INV_NUMERIC_FEATURES."""
        if not self.scorer_available:
            raise RuntimeError(
                "Payment scorer not loaded. Run ml_pipeline training and "
                "copy artifacts into backend/app/ml/models/."
            )
        X = pd.DataFrame([features])[INV_NUMERIC_FEATURES]
        return float(self.scorer.predict_proba(X)[0][1])


model_service = ModelService()
