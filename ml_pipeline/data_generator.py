
"""
Nova ML Pipeline — Synthetic Dataset Generator (v2)

Design principle: the root cause / paid-label is a NOISY, PROBABILISTIC
function of the observed features, never a deterministic if/else rule.
This is what stops the downstream model from just memorizing the generator
instead of learning a transferable pattern (see ml_pipeline/README.md /
project chat history for the full rationale).

Three layers, deliberately kept separate:
  1. Latent customer state (segment, "true" success rate / network quality)
     — never output directly, only surfaces as noise-corrupted features.
  2. Observed features — latent state + measurement noise, i.e. what a
     real payments system would actually have on hand at decision time.
  3. Label — a per-row propensity score per class, perturbed with Gumbel
     noise (soft-max sampling) and a small rate of pure label noise.

Two datasets:
  - generate_transaction_dataset()  -> 6-class root-cause classifier data
  - generate_invoice_dataset()      -> binary "did they pay" scorer data

Note on class count: ABANDONMENT and OVERDUE are resolved deterministically
from `status` in app/services/classifier.py's rule-based first pass — they
never reach the ML fallback, so they are intentionally excluded from the
6-class taxonomy trained here. Only genuinely ambiguous payment-failure
causes go through the model.
"""

import os

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Schema contract — training/validation scripts import these constants so
# the feature list lives in exactly one place.
# ---------------------------------------------------------------------------

TX_ID_COLUMNS = ["customer_id"]
TX_LABEL_COLUMN = "root_cause"
TX_CLASSES = [
    "INSUFFICIENT_FUNDS",
    "BANK_TIMEOUT",
    "CARD_EXPIRED",
    "MANDATE_REVOKED",
    "RISK_DECLINE",
    "NETWORK_ERROR",
]
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

INV_ID_COLUMNS = ["customer_id"]
INV_LABEL_COLUMN = "paid"
INV_NUMERIC_FEATURES = [
    "days_overdue",
    "invoice_amount",
    "customer_ontime_rate",
    "prior_broken_promises",
    "payment_history_length",
    "followup_count",
]


def _gumbel_noise(rng, shape):
    """Standard Gumbel(0,1) noise. Adding this to per-class scores and taking
    argmax is the Gumbel-max trick — equivalent to sampling from softmax(scores)
    without ever materializing the softmax. This is what turns clean scores
    into a genuinely probabilistic (non-deterministic) label."""
    u = rng.uniform(1e-12, 1 - 1e-12, size=shape)
    return -np.log(-np.log(u))


def generate_transaction_dataset(
    n=5000,
    seed=42,
    label_noise_rate=0.06,
    missing_rate=0.05,
    ambiguous_frac=0.12,
    signal_strength=1.8,
):
    """Synthetic failed-payment transactions for the root-cause classifier.

    Args:
        n: number of rows.
        seed: RNG seed (use a different seed for a held-out generalization
            check — see generate_train_and_holdout below).
        label_noise_rate: fraction of rows whose label is replaced with a
            uniformly random class after generation (simulates miscoding).
        missing_rate: fraction of rows with NaN in noisy/optional fields.
        ambiguous_frac: fraction of rows where class scores are deliberately
            flattened before noise is added, producing genuinely hard,
            low-confidence cases (these are what a confidence-based
            human-escalation gate should actually catch).
        signal_strength: multiplier applied to class scores for the
            non-ambiguous majority of rows, BEFORE Gumbel noise is added.
            At 1.0, even "easy" rows sit close to the noise floor and no
            prediction can ever be confidently correct — this creates a
            genuine gap between easy (high, trustworthy confidence) and
            ambiguous (low, correctly-untrustworthy confidence) rows, which
            an escalation gate needs to have something to actually separate.
            The specific confidence threshold that gate should use is a
            model property to be measured (see train_classifier.py's
            reliability curve), not a fixed number assumed up front.
    """
    rng = np.random.default_rng(seed)

    # ---- Layer 1: latent customer state (not output directly) ------------
    segment = rng.choice(["low", "mid", "high"], size=n, p=[0.45, 0.40, 0.15])
    segment_amount_scale = np.select(
        [segment == "low", segment == "mid", segment == "high"],
        [0.6, 1.0, 1.8],
    )
    true_success_rate = np.clip(
        rng.beta(5, 2, size=n) * np.where(segment == "low", 0.85, 1.0), 0.02, 0.99
    )
    true_network_quality = np.clip(rng.beta(6, 2, size=n), 0.02, 0.99)

    # ---- Layer 2: observed features = latent state + measurement noise ---
    day_of_month = rng.integers(1, 29, size=n)
    hour_of_day = rng.integers(0, 24, size=n)
    retry_count = np.clip(rng.poisson(0.8, size=n), 0, 3)
    is_mandate = rng.choice([0, 1], size=n, p=[0.42, 0.58])

    mandate_age_days = np.where(
        is_mandate == 1,
        rng.integers(1, 500, size=n).astype(float),
        np.nan,  # a one-off card txn genuinely has no mandate age
    )
    card_age_days = rng.integers(1, 1200, size=n).astype(float)
    subscription_tenure_days = rng.integers(0, 900, size=n)

    historical_success_rate = np.clip(
        true_success_rate + rng.normal(0, 0.05, size=n), 0.01, 0.99
    )
    network_quality_score = np.clip(
        true_network_quality + rng.normal(0, 0.05, size=n), 0.01, 0.99
    )

    base_amount = rng.lognormal(mean=6.3, sigma=0.9, size=n) * segment_amount_scale
    amount = np.clip(base_amount, 100, 200000)
    customer_avg = amount * rng.uniform(0.55, 1.45, size=n)
    amount_vs_customer_avg = amount / np.clip(customer_avg, 1, None)

    device_is_new = rng.choice([0, 1], size=n, p=[0.92, 0.08])
    has_error_description = rng.choice([0, 1], size=n, p=[0.22, 0.78])

    # ---- Layer 3: hidden root cause as a NOISY function of the features --
    scores = np.zeros((n, len(TX_CLASSES)))
    idx = {c: i for i, c in enumerate(TX_CLASSES)}
    mandate_age_filled = np.nan_to_num(mandate_age_days, nan=0.0)

    scores[:, idx["INSUFFICIENT_FUNDS"]] = (
        1.4 * (day_of_month >= 25)
        + 1.1 * (1 - historical_success_rate)
        + 0.5 * is_mandate
    )
    scores[:, idx["BANK_TIMEOUT"]] = (
        1.3 * (1 - network_quality_score) + 0.3 * is_mandate + 0.5
    )
    scores[:, idx["CARD_EXPIRED"]] = (
        1.0 * np.clip(card_age_days / 365 - 1.1, 0, 1.4)
        + 0.3 * (amount_vs_customer_avg > 1.2)
        - 0.3
    )
    scores[:, idx["MANDATE_REVOKED"]] = (
        2.2 * is_mandate * np.clip(mandate_age_filled / 365 - 0.7, 0, None) - 0.4
    )
    scores[:, idx["RISK_DECLINE"]] = (
        1.3 * (amount_vs_customer_avg > 1.5)
        + 1.6 * device_is_new
        + 0.2 * (subscription_tenure_days > 180)
        - 0.4
    )
    scores[:, idx["NETWORK_ERROR"]] = 1.6 * (1 - network_quality_score) - 0.3

    # Boost the "easy" majority so it's genuinely separable from noise, then
    # deliberately flatten scores for an "ambiguous" slice of rows so the
    # model also sees genuinely hard, low-confidence cases during training.
    scale = np.full(n, signal_strength)
    ambiguous_mask = rng.random(n) < ambiguous_frac
    scale[ambiguous_mask] = rng.uniform(0.1, 0.4, size=ambiguous_mask.sum())

    noisy_scores = scores * scale[:, None] + _gumbel_noise(rng, scores.shape)
    label_idx = noisy_scores.argmax(axis=1)

    # Pure label noise on top (mislabeled / miscoded real-world records).
    flip_mask = rng.random(n) < label_noise_rate
    label_idx = label_idx.copy()
    label_idx[flip_mask] = rng.integers(0, len(TX_CLASSES), size=flip_mask.sum())

    root_cause = np.array(TX_CLASSES)[label_idx]

    df = pd.DataFrame(
        {
            "customer_id": [f"cust_{i:05d}" for i in range(n)],
            "day_of_month": day_of_month,
            "hour_of_day": hour_of_day,
            "retry_count": retry_count,
            "is_mandate": is_mandate,
            "mandate_age_days": mandate_age_days,
            "card_age_days": card_age_days,
            "subscription_tenure_days": subscription_tenure_days,
            "customer_historical_success_rate": historical_success_rate,
            "amount": amount,
            "amount_vs_customer_avg": amount_vs_customer_avg,
            "network_quality_score": network_quality_score,
            "device_is_new": device_is_new,
            "has_error_description": has_error_description,
            "root_cause": root_cause,
        }
    )

    # ---- Layer 4: real-world missingness on top of otherwise-clean data --
    for col in ["network_quality_score", "customer_historical_success_rate"]:
        miss_mask = rng.random(n) < missing_rate
        df.loc[miss_mask, col] = np.nan

    return df


def generate_invoice_dataset(n=3000, seed=7, missing_rate=0.05, outlier_frac=0.02):
    """Synthetic B2B overdue-invoice data for the payment-probability scorer.

    Label is generated via logit -> sigmoid -> Bernoulli draw (not a
    threshold), plus an unobserved-factors noise term on the logit — this
    was already the right pattern in v1, kept here with added missingness
    and amount outliers for realism.
    """
    rng = np.random.default_rng(seed)

    days_overdue = rng.integers(1, 120, size=n)
    invoice_amount = rng.lognormal(mean=8.4, sigma=1.0, size=n)

    outlier_mask = rng.random(n) < outlier_frac
    invoice_amount = invoice_amount.copy()
    invoice_amount[outlier_mask] *= rng.uniform(3, 8, size=outlier_mask.sum())

    ontime_rate = np.clip(
        rng.beta(4, 2, size=n) + rng.normal(0, 0.04, size=n), 0.01, 0.99
    )
    broken_promises = rng.poisson(0.6, size=n)
    history_len = rng.integers(1, 40, size=n)
    followup_count = rng.integers(0, 5, size=n)

    logit = (
        2.4 * ontime_rate
        - 0.015 * days_overdue
        - 0.55 * broken_promises
        + 0.01 * np.minimum(history_len, 20)
        - 0.08 * followup_count
        - 0.3
        + rng.normal(0, 0.35, size=n)  # unobserved real-world factors
    )
    prob = 1 / (1 + np.exp(-logit))
    paid = rng.binomial(1, prob)

    df = pd.DataFrame(
        {
            "customer_id": [f"biz_{i:05d}" for i in range(n)],
            "days_overdue": days_overdue,
            "invoice_amount": invoice_amount,
            "customer_ontime_rate": ontime_rate,
            "prior_broken_promises": broken_promises,
            "payment_history_length": history_len,
            "followup_count": followup_count,
            "paid": paid,
        }
    )

    miss_mask = rng.random(n) < missing_rate
    df.loc[miss_mask, "customer_ontime_rate"] = np.nan

    return df


def generate_train_and_holdout(generator_fn, n_train, n_holdout, train_seed=42,
                                holdout_seed=2024, **kwargs):
    """Two independently-seeded batches. The holdout batch is NOT used for
    train/val split or hyperparameter tuning at all — it's your proxy for
    'unseen real-world data' because it wasn't generated with the same
    random draw as anything the model was tuned against."""
    train_df = generator_fn(n=n_train, seed=train_seed, **kwargs)
    holdout_df = generator_fn(n=n_holdout, seed=holdout_seed, **kwargs)
    return train_df, holdout_df


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(out_dir, exist_ok=True)

    tx_train, tx_holdout = generate_train_and_holdout(
        generate_transaction_dataset, n_train=5000, n_holdout=1000
    )
    inv_train, inv_holdout = generate_train_and_holdout(
        generate_invoice_dataset, n_train=3000, n_holdout=600
    )

    tx_train.to_csv(os.path.join(out_dir, "transactions_train.csv"), index=False)
    tx_holdout.to_csv(os.path.join(out_dir, "transactions_holdout.csv"), index=False)
    inv_train.to_csv(os.path.join(out_dir, "invoices_train.csv"), index=False)
    inv_holdout.to_csv(os.path.join(out_dir, "invoices_holdout.csv"), index=False)

    print(f"Transactions: train={len(tx_train)}, holdout={len(tx_holdout)}")
    print(tx_train["root_cause"].value_counts())
    print(f"\nInvoices: train={len(inv_train)}, holdout={len(inv_holdout)}")
    print(inv_train["paid"].value_counts())
    print(f"\nSaved CSVs to {out_dir}/")
