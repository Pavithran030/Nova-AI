import numpy as np
import pandas as pd

def generate_transaction_dataset(n=5000, seed=42):
    """Generates synthetic failed transaction data for Model 1 (Root-Cause Classifier).
    
    Taxonomy of 8 Root Causes:
    - INSUFFICIENT_FUNDS
    - BANK_TIMEOUT
    - CARD_EXPIRED
    - MANDATE_REVOKED
    - RISK_DECLINE
    - NETWORK_ERROR
    - ABANDONMENT
    - OVERDUE
    """
    rng = np.random.default_rng(seed)
    day_of_month = rng.integers(1, 29, size=n)
    hour_of_day = rng.integers(0, 24, size=n)
    retry_count = rng.integers(0, 4, size=n)  # Max 4 attempts per NPCI Autopay rules
    amount = rng.lognormal(mean=6.5, sigma=0.8, size=n)  # Realistic INR distribution
    customer_avg = amount * rng.uniform(0.6, 1.4, size=n)
    success_rate = rng.beta(5, 2, size=n)  # Historical customer success rate
    mandate_age = rng.integers(1, 400, size=n)
    is_mandate = rng.choice([0, 1], size=n, p=[0.4, 0.6])
    device_hash = rng.integers(1000, 9999, size=n)
    subscription_tenure = rng.integers(0, 730, size=n)

    root_cause = []
    for i in range(n):
        r = rng.random()
        # Month-end low balance pattern
        if day_of_month[i] > 24 and success_rate[i] < 0.6 and r < 0.75:
            root_cause.append("INSUFFICIENT_FUNDS")
        # Old mandate revoked pattern
        elif is_mandate[i] and mandate_age[i] > 365 and r < 0.6:
            root_cause.append("MANDATE_REVOKED")
        # Fraud risk decline false positive pattern
        elif amount[i] > customer_avg[i] * 1.5 and subscription_tenure[i] > 180 and r < 0.3:
            root_cause.append("RISK_DECLINE")
        # Transient network error
        elif r < 0.10:
            root_cause.append("NETWORK_ERROR")
        # Bank gateway timeout
        elif r < 0.22:
            root_cause.append("BANK_TIMEOUT")
        # Expired card on file
        elif amount[i] > customer_avg[i] * 1.3 and r < 0.4:
            root_cause.append("CARD_EXPIRED")
        # Cart checkout abandonment
        elif not is_mandate[i] and r < 0.35:
            root_cause.append("ABANDONMENT")
        # B2B invoice overdue
        elif r < 0.15:
            root_cause.append("OVERDUE")
        else:
            root_cause.append(rng.choice(
                ["INSUFFICIENT_FUNDS", "BANK_TIMEOUT", "ABANDONMENT", "NETWORK_ERROR"],
                p=[0.35, 0.25, 0.25, 0.15]
            ))

    return pd.DataFrame({
        "day_of_month": day_of_month,
        "hour_of_day": hour_of_day,
        "retry_count": retry_count,
        "amount": amount,
        "amount_vs_customer_avg": amount / customer_avg,
        "customer_historical_success_rate": success_rate,
        "mandate_age_days": mandate_age,
        "is_mandate": is_mandate,
        "device_fingerprint_hash": device_hash,
        "subscription_tenure_days": subscription_tenure,
        "root_cause": root_cause,
    })


def generate_invoice_dataset(n=3000, seed=7):
    """Generates synthetic B2B overdue invoice dataset for Model 2 (Payment Scorer)."""
    rng = np.random.default_rng(seed)
    days_overdue = rng.integers(1, 120, size=n)
    invoice_amount = rng.lognormal(mean=8.5, sigma=1.0, size=n)  # INR amounts
    ontime_rate = rng.beta(4, 2, size=n)
    broken_promises = rng.poisson(0.6, size=n)
    history_len = rng.integers(1, 40, size=n)
    followup_count = rng.integers(0, 5, size=n)

    # Underlying hidden logistic probability function
    logit = (
        2.5 * ontime_rate
        - 0.015 * days_overdue
        - 0.6 * broken_promises
        + 0.01 * np.minimum(history_len, 20)
        - 0.1 * followup_count
        - 0.3
    )
    prob = 1 / (1 + np.exp(-logit))
    paid = rng.binomial(1, prob)

    return pd.DataFrame({
        "days_overdue": days_overdue,
        "invoice_amount": invoice_amount,
        "customer_ontime_rate": ontime_rate,
        "prior_broken_promises": broken_promises,
        "payment_history_length": history_len,
        "followup_count": followup_count,
        "paid": paid,
    })

if __name__ == "__main__":
    tx_df = generate_transaction_dataset()
    inv_df = generate_invoice_dataset()
    print(f"Generated {len(tx_df)} transaction records across classes:")
    print(tx_df["root_cause"].value_counts())
    print(f"\nGenerated {len(inv_df)} invoice records (Paid balance: {inv_df['paid'].value_counts().to_dict()})")
