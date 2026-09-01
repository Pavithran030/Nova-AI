from datetime import datetime, timedelta

import pytest

from app.models.merchant import Merchant
from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.utils.synthetic_data import seed_policy_config
from app.services.policy_engine import decide_action


def _make_merchant(db):
    m = Merchant(name="Test Merchant", tenant_id="t1")
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def test_decide_action_known_error_code_uses_rule_based_policy(db):
    seed_policy_config(db)
    merchant = _make_merchant(db)
    tx = Transaction(
        merchant_id=merchant.id, customer_id="cust_1", amount=1000,
        status="failed", error_code="INSUFF_BALANCE",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    action = decide_action(db, "transaction", tx.id)

    assert action.root_cause == "INSUFFICIENT_FUNDS"
    assert action.root_cause_confidence == 0.85
    assert action.action_type == "delay_retry"  # seeded policy for this root cause
    assert action.stop_reason is None


def test_decide_action_invoice_uses_overdue_policy(db):
    seed_policy_config(db)
    merchant = _make_merchant(db)
    inv = Invoice(
        merchant_id=merchant.id, customer_id="cust_2", amount=5000,
        due_date=datetime.now() - timedelta(days=10), status="overdue", days_overdue=10,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    action = decide_action(db, "invoice", inv.id)

    assert action.root_cause == "OVERDUE"
    assert action.action_type == "b2b_follow_up"


def test_decide_action_unknown_entity_type_raises(db):
    with pytest.raises(ValueError):
        decide_action(db, "not_a_real_type", "whatever")


def test_decide_action_missing_transaction_raises(db):
    with pytest.raises(ValueError):
        decide_action(db, "transaction", "does-not-exist")


def test_decide_action_well_formed_for_ambiguous_code(db):
    """An unmapped error code hits the rule-based fallback (confidence
    0.65) -- classify_transaction then either uses the trained ML
    classifier (if artifacts are present) or keeps the rule-based fallback
    result. This test asserts the result is always well-formed regardless
    of whether ML artifacts happen to exist in the running environment,
    rather than asserting on which path was taken."""
    seed_policy_config(db)
    merchant = _make_merchant(db)
    tx = Transaction(
        merchant_id=merchant.id, customer_id="cust_3", amount=2000,
        status="failed", error_code="TOTALLY_UNMAPPED_CODE_XYZ",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    action = decide_action(db, "transaction", tx.id)

    assert action.root_cause is not None
    assert action.root_cause_confidence is not None
    assert action.action_type is not None
    if action.action_type == "ESCALATE_TO_HUMAN":
        assert action.stop_reason == "low_confidence"
    else:
        assert action.stop_reason is None
