from app.services.classifier import classify_root_cause

def test_rule_based_classification():
    cause, conf, reason = classify_root_cause("INSUFF_FUNDS", "failed")
    assert cause == "INSUFFICIENT_FUNDS"
    assert conf == 0.85

    cause, conf, reason = classify_root_cause("UPI_TIMEOUT", "failed")
    assert cause == "BANK_TIMEOUT"

    cause, conf, reason = classify_root_cause("CARD_EXPIRED_001", "failed")
    assert cause == "CARD_EXPIRED"

    cause, conf, reason = classify_root_cause("MANDATE_REVOKED", "failed")
    assert cause == "MANDATE_REVOKED"

    cause, conf, reason = classify_root_cause(None, "abandoned")
    assert cause == "ABANDONMENT"

    cause, conf, reason = classify_root_cause(None, "overdue")
    assert cause == "OVERDUE"
