import os
import joblib
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.calibration import calibration_curve, CalibratedClassifierCV

from data_generator import generate_invoice_dataset

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def train_scorer():
    print("=" * 60)
    print(" Nova ML Pipeline — Model 2: Payment Probability Scorer ")
    print("=" * 60)

    # 1. Load Data
    df = generate_invoice_dataset(n=3000, seed=7)
    X = df.drop(columns=["paid"])
    y = df["paid"]

    print(f"\n[1/5] Loaded dataset with {len(df)} B2B invoice samples:")
    print(y.value_counts().to_dict())

    # 2. Split Data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    # 3. Model Training
    print("\n[2/5] Training Logistic Regression Scorer...")
    scorer = LogisticRegression(max_iter=1000, random_state=42)
    scorer.fit(X_train, y_train)

    # 4. Evaluation
    print("\n[3/5] Evaluating model performance & probability calibration...")
    probs = scorer.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, probs)
    brier = brier_score_loss(y_test, probs)

    print(f"  AUC Score: {auc:.4f} (Ranking accuracy)")
    print(f"  Brier Score: {brier:.4f} (Lower = better calibrated)")

    print("\nModel Coefficients (Interpretability Evidence):")
    for name, coef in zip(X.columns, scorer.coef_[0]):
        impact = "↑ payment odds" if coef > 0 else "↓ payment odds"
        print(f"  {name:25s}: {coef:+.4f}  ({impact})")
    print(f"  {'intercept':25s}: {scorer.intercept_[0]:+.4f}")

    # Calibration Check & Fallback
    if brier > 0.15:
        print("\n  ⚠️ Brier score > 0.15. Applying CalibratedClassifierCV...")
        calibrated = CalibratedClassifierCV(scorer, cv=5, method="sigmoid")
        calibrated.fit(X_train, y_train)
        calibrated_probs = calibrated.predict_proba(X_test)[:, 1]
        new_brier = brier_score_loss(y_test, calibrated_probs)
        print(f"  Calibrated Brier Score: {new_brier:.4f}")
        if new_brier < brier:
            scorer = calibrated
            probs = calibrated_probs

    # 5. Export Calibration Curve Plot
    print("\n[4/5] Exporting calibration curve plot...")
    prob_true, prob_pred = calibration_curve(y_test, probs, n_bins=10)
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(prob_pred, prob_true, marker="o", color="#3B6CF5", label="Nova Scorer")
    ax.plot([0, 1], [0, 1], "--", color="gray", label="Perfect Calibration")
    ax.set_xlabel("Predicted Probability P(payment)")
    ax.set_ylabel("Observed Actual Frequency")
    ax.set_title(f"Nova — Payment Scorer: Calibration Curve\nAUC = {auc:.3f}, Brier = {brier:.4f}")
    ax.legend()
    plt.tight_layout()
    calib_path = os.path.join(ARTIFACTS_DIR, "calibration_curve.png")
    plt.savefig(calib_path, dpi=150)
    print(f" Saved: {calib_path}")
    plt.close()

    # 6. Save Model File
    print("\n[5/5] Saving model binary file...")
    model_file = os.path.join(ARTIFACTS_DIR, "payment_scorer.joblib")
    joblib.dump(scorer, model_file)

    print(f" Saved model: {model_file}")
    print("=" * 60)

if __name__ == "__main__":
    train_scorer()
