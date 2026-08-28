from app.ml.model_service import model_service


def calculate_payment_probability(on_time_rate: float, days_overdue: int, broken_promises: int, history_len: int) -> float:
    # Hand-tuned fallback formula, used when the trained scorer isn't loaded:
    # P(payment) = max(0.05, min(0.95, 0.8 * on_time_rate - 0.01 * days_overdue - 0.15 * broken_promises + 0.005 * min(history_len, 20)))
    prob = 0.8 * on_time_rate - 0.01 * days_overdue - 0.15 * broken_promises + 0.005 * min(history_len, 20)
    return max(0.05, min(0.95, prob))


def calculate_payment_probability_ml(
    days_overdue: int,
    invoice_amount: float,
    customer_ontime_rate: float,
    prior_broken_promises: int,
    payment_history_length: int,
    followup_count: int,
) -> float:
    """Trained logistic-regression scorer (ml_pipeline/train_scorer.py).
    All six features are real columns already tracked on Invoice /
    CustomerFeature — unlike the classifier, no defaults are needed here.
    Falls back to the hand-tuned formula above if the model isn't loaded,
    so callers never have to branch on availability themselves."""
    if model_service.scorer_available:
        features = {
            "days_overdue": days_overdue,
            "invoice_amount": invoice_amount,
            "customer_ontime_rate": customer_ontime_rate,
            "prior_broken_promises": prior_broken_promises,
            "payment_history_length": payment_history_length,
            "followup_count": followup_count,
        }
        return model_service.predict_payment_probability(features)
    return calculate_payment_probability(
        customer_ontime_rate, days_overdue, prior_broken_promises, payment_history_length
    )


def expected_recovery_value(amount: float, prob: float) -> float:
    return amount * prob
