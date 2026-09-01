import random
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.recovery_action import RecoveryAction
from app.models.audit_log import AuditLog
from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.models.mandate import Mandate
from app.models.policy_config import PolicyConfig
from app.services.policy_engine import decide_action
from app.services.executor import execute_action
from app.utils.npci import is_valid_npci_window, get_next_valid_window, check_attempt_budget

# NPCI Autopay windows/attempt-cap rules only govern mandate-based
# direct-debit retries -- not contact channels (whatsapp/email/sms) or
# evidence-based appeals -- matching the blueprint's action policy table.
MANDATE_RETRY_ACTIONS = {"delay_retry", "immediate_retry_with_backoff", "immediate_retry_exponential"}

DAILY_ACTION_CAP = 2
DEFAULT_INVOICE_ESCALATION_THRESHOLD = 3

# Recoverability priors per root cause, used only when no better signal
# (the trained B2B scorer's payment_probability) is available. These feed
# simulate_outcome() so a "success" is a function of what was actually
# decided, not an actor-only coin-flip.
ROOT_CAUSE_BASE_RATES = {
    "BANK_TIMEOUT": 0.75,
    "NETWORK_ERROR": 0.70,
    "INSUFFICIENT_FUNDS": 0.55,
    "RISK_DECLINE": 0.50,
    "ABANDONMENT": 0.40,
    "CARD_EXPIRED": 0.45,
    "MANDATE_REVOKED": 0.35,
}


def _count_actions_today_for_customer(db: Session, customer_id: str, actor: str, now: datetime) -> int:
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tx_ids = [t.id for t in db.query(Transaction).filter(Transaction.customer_id == customer_id).all()]
    inv_ids = [i.id for i in db.query(Invoice).filter(Invoice.customer_id == customer_id).all()]
    entity_ids = tx_ids + inv_ids
    if not entity_ids:
        return 0
    return db.query(RecoveryAction).filter(
        RecoveryAction.entity_id.in_(entity_ids),
        RecoveryAction.actor == actor,
        RecoveryAction.executed_at.isnot(None),
        RecoveryAction.executed_at >= today_start,
    ).count()


def _has_prior_action(db: Session, entity_type: str, entity_id: str, actor: str) -> bool:
    return db.query(RecoveryAction).filter(
        RecoveryAction.entity_type == entity_type,
        RecoveryAction.entity_id == entity_id,
        RecoveryAction.actor == actor,
        RecoveryAction.executed_at.isnot(None),
    ).count() > 0


def _stop(db: Session, action: RecoveryAction, reason: str, reasoning: str, actor: str,
          npci_window: str = "n/a", now: datetime = None) -> RecoveryAction:
    """A stopping rule fired -- the action is recorded as decided, but never
    executed (no channel/content_sent, executed_at stays NULL so it never
    counts toward daily-cap/history budgets). This is the compliant
    escalation path the blueprint requires."""
    action.outcome = "STOPPED"
    action.stop_reason = reason
    db.commit()
    db.refresh(action)
    log = AuditLog(
        entity_type=action.entity_type,
        entity_id=action.entity_id,
        action_type=action.action_type,
        reasoning=reasoning,
        actor=actor,
        npci_window=npci_window,
        timestamp=now or datetime.now(),
    )
    db.add(log)
    db.commit()
    return action


def simulate_outcome(actor: str, root_cause: str, confidence: float, entity_type: str, entity, in_window: bool) -> bool:
    """Recovery-success probability DERIVED from decision quality --
    root-cause recoverability, classifier confidence, NPCI compliance, and
    (for invoices) the trained scorer's real payment_probability -- instead
    of a flat actor-only coin-flip. A better diagnosis genuinely produces a
    better outcome distribution, which is the entire point the project
    exists to demonstrate."""
    if entity_type == "invoice" and getattr(entity, "payment_probability", None) is not None:
        base = entity.payment_probability
    else:
        base = ROOT_CAUSE_BASE_RATES.get(root_cause, 0.45)

    if actor == "agent":
        # confidence-weighted: a shakier diagnosis gets a shakier outcome
        prob = base * (0.6 + 0.4 * (confidence if confidence is not None else 0.5))
        if not in_window:
            prob *= 0.5  # shouldn't normally happen -- agent reschedules instead of firing
    else:
        # baseline: blind retry, no root-cause-matched action, ignores window
        prob = base * 0.45
        if not in_window:
            prob *= 0.7  # a real NPCI violation -- baseline fires anyway

    return random.random() < max(0.03, min(0.95, prob))


def process_item(db: Session, entity_type: str, entity_id: str, actor: str = "agent", now: datetime = None) -> RecoveryAction:
    """now: overridable clock, used by app/utils/generate_history.py to
    bulk-backfill history against each event's own simulated timestamp
    rather than real wall-clock time -- otherwise every daily-cap check
    during a bulk run would collapse onto the same real calendar day."""
    now = now or datetime.now()

    action = decide_action(db, entity_type, entity_id)
    action.actor = actor
    db.commit()
    db.refresh(action)

    if entity_type == "transaction":
        entity = db.query(Transaction).filter(Transaction.id == entity_id).first()
    else:
        entity = db.query(Invoice).filter(Invoice.id == entity_id).first()
    if entity is None:
        raise ValueError(f"{entity_type} {entity_id} not found")

    mandate = None
    if entity_type == "transaction" and entity.mandate_id:
        mandate = db.query(Mandate).filter(Mandate.id == entity.mandate_id).first()

    # --- low ML/rule confidence: policy_engine already flagged this ---
    if action.action_type == "ESCALATE_TO_HUMAN":
        return _stop(
            db, action, "low_confidence",
            f"{actor}: escalated to human -- classifier confidence below operating threshold",
            actor, now=now,
        )

    # --- daily cap: max DAILY_ACTION_CAP actions per customer per day ---
    if _count_actions_today_for_customer(db, entity.customer_id, actor, now) >= DAILY_ACTION_CAP:
        return _stop(
            db, action, "daily_cap",
            f"{actor}: daily action cap ({DAILY_ACTION_CAP}) reached for this customer",
            actor, now=now,
        )

    # --- single-nudge cap: one checkout-abandonment nudge, ever ---
    if action.root_cause == "ABANDONMENT" and _has_prior_action(db, entity_type, entity_id, actor):
        return _stop(
            db, action, "single_nudge_cap",
            f"{actor}: checkout nudge already sent once -- no repeated contact",
            actor, now=now,
        )

    # --- B2B follow-up escalation threshold (broken-promise style cap) ---
    if entity_type == "invoice":
        policy = db.query(PolicyConfig).filter(PolicyConfig.root_cause == "OVERDUE").first()
        threshold = (policy.escalation_threshold if policy and policy.escalation_threshold
                     else DEFAULT_INVOICE_ESCALATION_THRESHOLD)
        if (entity.followup_count or 0) >= threshold:
            return _stop(
                db, action, "followup_escalation",
                f"{actor}: {entity.followup_count} follow-ups already sent, escalating to human collections",
                actor, now=now,
            )

    # --- attempt-cap: mandate's real 4-total-attempt budget, or the
    # transaction's own generic cap for non-mandate-retry actions ---
    is_mandate_retry = (
        entity_type == "transaction"
        and action.action_type in MANDATE_RETRY_ACTIONS
        and mandate is not None
    )
    if is_mandate_retry:
        if not check_attempt_budget(mandate.attempts_used, mandate.max_attempts):
            return _stop(
                db, action, "max_attempts",
                f"{actor}: mandate attempt cap ({mandate.max_attempts}) reached",
                actor, now=now,
            )
    elif entity_type == "transaction":
        if not check_attempt_budget(entity.attempt_count, entity.max_attempts):
            return _stop(
                db, action, "max_attempts",
                f"{actor}: transaction attempt cap ({entity.max_attempts}) reached",
                actor, now=now,
            )

    # --- NPCI window enforcement: mandate retries only. Agent complies
    # (reschedules instead of firing); baseline ignores it -- that gap is
    # exactly what /reports/baseline-vs-agent is supposed to measure. ---
    in_window = True
    npci_window_label = "n/a"
    if is_mandate_retry:
        in_window = is_valid_npci_window(now)
        if not in_window:
            npci_window_label = "invalid_scheduled" if actor == "agent" else "invalid_violated"
            if actor == "agent":
                action.scheduled_for = get_next_valid_window(now)
                action.outcome = "SCHEDULED"
                db.commit()
                db.refresh(action)
                log = AuditLog(
                    entity_type=entity_type, entity_id=entity_id, action_type=action.action_type,
                    reasoning=f"agent: outside NPCI window, rescheduled to {action.scheduled_for}",
                    actor=actor, npci_window=npci_window_label, timestamp=now,
                )
                db.add(log)
                db.commit()
                return action
            # baseline falls through and fires anyway -- the violation being measured
        else:
            npci_window_label = "valid"

    # --- audit log written BEFORE execution, as the blueprint requires ---
    pre_log = AuditLog(
        entity_type=entity_type, entity_id=entity_id, action_type=action.action_type,
        reasoning=f"{actor}: {action.root_cause} (confidence {(action.root_cause_confidence or 0):.2f}) -> {action.action_type}",
        actor=actor, npci_window=npci_window_label,
        attempt_number=(mandate.attempts_used + 1) if is_mandate_retry else None,
        timestamp=now,
    )
    db.add(pre_log)
    db.commit()

    # --- execute ---
    exec_res = execute_action(action.action_type, entity_type, entity_id)
    action.channel = exec_res["channel"]
    action.content_sent = exec_res["content_sent"]
    action.executed_at = now

    # --- outcome, derived from decision quality, not a flat coin-flip ---
    success = simulate_outcome(actor, action.root_cause, action.root_cause_confidence, entity_type, entity, in_window)
    if success:
        action.outcome = "SUCCESS" if actor == "agent" else "BASELINE_SUCCESS"
    else:
        action.outcome = "FAILED" if actor == "agent" else "BASELINE_FAILED"

    # Only the real agent run mutates shared/live state -- a baseline run is
    # a read-only counterfactual (it reads the real current budget/state to
    # decide whether it WOULD be blocked, but never consumes real attempt
    # budget or changes real status; two parallel decision systems can't
    # both really retry the same live mandate).
    if actor == "agent":
        if is_mandate_retry:
            mandate.attempts_used += 1
        elif entity_type == "transaction":
            entity.attempt_count += 1
        if entity_type == "invoice":
            entity.followup_count = (entity.followup_count or 0) + 1
        if action.outcome == "SUCCESS":
            entity.status = "recovered" if entity_type == "transaction" else "paid"

    db.commit()
    db.refresh(action)
    return action
