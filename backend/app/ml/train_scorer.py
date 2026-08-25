import os
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.calibration import calibration_curve, CalibratedClassifierCV
import joblib

from app.utils.synthetic_data import generate_invoice_batch

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODEL_DIR, exist_ok=True)

def train_payment_scorer():
    """Train the B2B payment probability scorer.
    
    Outputs:
      - payment_probability_model.joblib
      - calibration_curve.png
    """
    df = generate_invoice_batch(n=2000)
    X = df.drop(columns=["paid"])
    y = df["paid"]

    print(f"Class balance: {y.value_counts().to_dict()}")
    print()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    scorer = LogisticRegression(max_iter=1000)
    scorer.fit(X_train, y_train)

    probs = scorer.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, probs)
    brier = brier_score_loss(y_test, probs)
    print(f"AUC: {auc:.4f}")
    print(f"Brier score (lower = better calibrated): {brier:.4f}")
    print()

    print("=== Coefficients (Interpretability Evidence) ===")
    for name, coef in zip(X.columns, scorer.coef_[0]):
        direction = "↑ payment odds" if coef > 0 else "↓ payment odds"
        print(f"  {name}: {coef:+.3f}  ({direction})")
    print(f"  intercept: {scorer.intercept_[0]:+.3f}")
    print()

    prob_true, prob_pred = calibration_curve(y_test, probs, n_bins=10)
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(prob_pred, prob_true, marker="o", label="Nova Scorer")
    ax.plot([0, 1], [0, 1], "--", color="gray", label="Perfectly calibrated")
    ax.set_xlabel("Predicted probability")
    ax.set_ylabel("Observed frequency")
    ax.set_title(f"Nova — Payment Scorer: Calibration Curve\nAUC={auc:.3f}, Brier={brier:.4f}")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(MODEL_DIR, "calibration_curve.png"), dpi=150)
    print("Saved calibration_curve.png")

    if brier > 0.15:
        print("\nBrier score > 0.15 — applying CalibratedClassifierCV...")
        calibrated = CalibratedClassifierCV(scorer, cv=5, method="sigmoid")
        calibrated.fit(X_train, y_train)
        new_brier = brier_score_loss(y_test, calibrated.predict_proba(X_test)[:, 1])
        print(f"  Calibrated Brier score: {new_brier:.4f}")
        if new_brier < brier:
            scorer = calibrated
            print("  Using calibrated model.")

    joblib.dump(scorer, os.path.join(MODEL_DIR, "payment_probability_model.joblib"))
    print(f"\nModel successfully saved to {MODEL_DIR}/")

    return scorer

if __name__ == "__main__":
    train_payment_scorer()
