from datetime import datetime
from typing import Tuple

from sqlalchemy.orm import Session

from app.ml.model_service import model_service

# Neutral defaults for the three trained features the current DB schema
# doesn't track yet (card issue date, live network-quality signal, and
# subscription start date aren't captured anywhere today). These are the
# population means from the ml_pipeline training distributions, so the
# model treats them as "unknown/average" rather than a value that skews
# the prediction. Replace with real columns once those signals are tracked.
DEFAULT_CARD_AGE_DAYS = 600.0
DEFAULT_NETWORK_QUALITY_SCORE = 0.75
DEFAULT_SUBSCRIPTION_TENURE_DAYS = 450.0


def classify_root_cause(error_code: str, status: str) -> Tuple[str, float, str]:
    """Rule-based first pass. Deterministic, free, and 100%-explainable for
    every code it recognizes — this stays the primary path; ML only ever
    gets consulted for the two fallback branches below (see
    classify_transaction), matching the "rules first, ML for ambiguous
    cases" design from the project blueprint."""
    if status == 'abandoned':
        return 'ABANDONMENT', 0.85, 'Status is abandoned'
    if status == 'overdue':
        return 'OVERDUE', 0.85, 'Status is overdue'

    if not error_code:
        return 'BANK_TIMEOUT', 0.65, 'No error code provided, defaulting'

    error_code = error_code.upper()

    if any(keyword in error_code for keyword in ['INSUFF', 'BAL', 'NSF']):
        return 'INSUFFICIENT_FUNDS', 0.85, 'Matches insufficient funds pattern'
    if any(keyword in error_code for keyword in ['TIMEOUT', 'TIME']):
        return 'BANK_TIMEOUT', 0.85, 'Matches bank timeout pattern'
    if any(keyword in error_code for keyword in ['EXPIRED', 'EXP']):
        return 'CARD_EXPIRED', 0.85, 'Matches card expired pattern'
    if any(keyword in error_code for keyword in ['REVOKE', 'MANDATE']):
        return 'MANDATE_REVOKED', 0.85, 'Matches mandate revoked pattern'
    if any(keyword in error_code for keyword in ['RISK', 'FRAUD', 'DECLINE']):
        return 'RISK_DECLINE', 0.85, 'Matches risk decline pattern'
    if any(keyword in error_code for keyword in ['NETWORK', 'CONN']):
        return 'NETWORK_ERROR', 0.85, 'Matches network error pattern'

    return 'BANK_TIMEOUT', 0.65, 'Fallback applied'


def _build_transaction_features(tx, mandate, feature) -> dict:
    now = datetime.now()
    is_mandate = 1 if tx.mandate_id else 0

    mandate_age_days = 0.0
    if mandate is not None and mandate.created_at:
        mandate_age_days = float((now - mandate.created_at).days)

    avg_amount = feature.avg_transaction_amount if feature and feature.avg_transaction_amount else tx.amount
    amount_vs_avg = (tx.amount / avg_amount) if avg_amount else 1.0
    success_rate = (
        feature.historical_success_rate
        if feature is not None and feature.historical_success_rate is not None
        else 0.7
    )

    return {
        "day_of_month": now.day,
        "hour_of_day": now.hour,
        "retry_count": min(tx.attempt_count or 0, 3),
        "is_mandate": is_mandate,
        "mandate_age_days": mandate_age_days,
        "card_age_days": DEFAULT_CARD_AGE_DAYS,
        "subscription_tenure_days": DEFAULT_SUBSCRIPTION_TENURE_DAYS,
        "customer_historical_success_rate": success_rate,
        "amount": tx.amount,
        "amount_vs_customer_avg": amount_vs_avg,
        "network_quality_score": DEFAULT_NETWORK_QUALITY_SCORE,
        "device_is_new": 0,
        "has_error_description": 1 if tx.error_description else 0,
    }


def classify_transaction(db: Session, tx) -> Tuple[str, float, str, bool]:
    """Rules-first, ML-fallback classification for a Transaction row.

    Returns (root_cause, confidence, reasoning, below_confidence_threshold).
    below_confidence_threshold is always False for rule/status matches
    (those are deterministic, not probabilistic) — it's only ever True when
    the ML fallback fired and scored under model_service.confidence_threshold,
    which is the empirically-derived value from classifier_metadata.json,
    not an assumed constant.
    """
    root_cause, confidence, reason = classify_root_cause(tx.error_code, tx.status)

    # confidence < 0.85 marks the two "fell through to a generic guess"
    # branches in classify_root_cause (no error_code, or an unmapped code) —
    # exactly the ambiguous case the ML model was trained to resolve.
    if confidence < 0.85 and model_service.classifier_available:
        from app.models.mandate import Mandate
        from app.models.customer_feature import CustomerFeature

        mandate = (
            db.query(Mandate).filter(Mandate.id == tx.mandate_id).first()
            if tx.mandate_id else None
        )
        feature = (
            db.query(CustomerFeature)
            .filter(CustomerFeature.customer_id == tx.customer_id)
            .first()
        )

        features = _build_transaction_features(tx, mandate, feature)
        ml_root_cause, ml_confidence, below_threshold = model_service.predict_root_cause(features)
        reason = (
            f"Rule-based pass was ambiguous ({reason}); ML classifier predicted "
            f"{ml_root_cause} with {ml_confidence * 100:.1f}% confidence"
            + (" — below threshold, escalating to human review" if below_threshold else "")
        )
        return ml_root_cause, ml_confidence, reason, below_threshold

    return root_cause, confidence, reason, False
