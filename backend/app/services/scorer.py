def calculate_payment_probability(on_time_rate: float, days_overdue: int, broken_promises: int, history_len: int) -> float:
    # Simple formula (no ML):
    # P(payment) = max(0.05, min(0.95, 0.8 * on_time_rate - 0.01 * days_overdue - 0.15 * broken_promises + 0.005 * min(history_len, 20)))
    prob = 0.8 * on_time_rate - 0.01 * days_overdue - 0.15 * broken_promises + 0.005 * min(history_len, 20)
    return max(0.05, min(0.95, prob))

def expected_recovery_value(amount: float, prob: float) -> float:
    return amount * prob
