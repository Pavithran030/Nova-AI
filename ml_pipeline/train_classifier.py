import os
import joblib
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay
from xgboost import XGBClassifier

from data_generator import generate_transaction_dataset

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def train_classifier():
    print("=" * 60)
    print(" Nova ML Pipeline — Model 1: Root-Cause Classifier ")
    print("=" * 60)

    # 1. Load Data
    df = generate_transaction_dataset(n=5000, seed=42)
    X = df.drop(columns=["root_cause"])
    y = df["root_cause"]

    print(f"\n[1/5] Loaded dataset with {len(df)} samples across 8 root-cause classes:")
    print(y.value_counts())

    # 2. Encode Labels
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, stratify=y_encoded, random_state=42
    )

    # 3. Model Training
    print("\n[2/5] Training XGBoost Multi-Class Classifier...")
    model = XGBClassifier(
        n_estimators=250,
        max_depth=5,
        learning_rate=0.08,
        objective="multi:softprob",
        eval_metric="mlogloss",
        random_state=42
    )
    model.fit(X_train, y_train)

    # 4. Evaluation
    print("\n[3/5] Evaluating performance on test set...")
    preds = model.predict(X_test)
    probas = model.predict_proba(X_test)

    print("\nClassification Report:")
    print(classification_report(y_test, preds, target_names=le.classes_))

    # 5. Export Plots & Artifacts
    print("\n[4/5] Exporting evaluation plots...")
    
    # Plot 1: Confusion Matrix
    cm = confusion_matrix(y_test, preds)
    fig, ax = plt.subplots(figsize=(10, 8))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=le.classes_)
    disp.plot(ax=ax, cmap="Blues", xticks_rotation=45)
    ax.set_title("Nova — Model 1: Root-Cause Classifier Confusion Matrix")
    plt.tight_layout()
    cm_path = os.path.join(ARTIFACTS_DIR, "confusion_matrix.png")
    plt.savefig(cm_path, dpi=150)
    print(f" Saved: {cm_path}")
    plt.close()

    # Plot 2: Feature Importances
    importances = model.feature_importances_
    sorted_idx = np.argsort(importances)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(range(len(sorted_idx)), importances[sorted_idx], color="#3B6CF5")
    ax.set_yticks(range(len(sorted_idx)))
    ax.set_yticklabels(X.columns[sorted_idx])
    ax.set_title("Nova — Model 1: Feature Importances (Explainability)")
    ax.set_xlabel("Importance Score")
    plt.tight_layout()
    fi_path = os.path.join(ARTIFACTS_DIR, "feature_importance.png")
    plt.savefig(fi_path, dpi=150)
    print(f" Saved: {fi_path}")
    plt.close()

    # Plot 3: Confidence Score Distribution
    max_probas = np.max(probas, axis=1)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(max_probas, bins=20, color="#12875A", edgecolor="black", alpha=0.7)
    ax.axvline(0.70, color="#D13438", linestyle="--", linewidth=2, label="Confidence Threshold (0.7)")
    ax.set_title("Nova — Classifier Confidence Score Distribution")
    ax.set_xlabel("Max Predicted Probability")
    ax.set_ylabel("Count")
    ax.legend()
    plt.tight_layout()
    conf_path = os.path.join(ARTIFACTS_DIR, "confidence_distribution.png")
    plt.savefig(conf_path, dpi=150)
    print(f" Saved: {conf_path}")
    plt.close()

    # 6. Save Model Files
    print("\n[5/5] Saving model binary files...")
    model_file = os.path.join(ARTIFACTS_DIR, "root_cause_model.joblib")
    encoder_file = os.path.join(ARTIFACTS_DIR, "root_cause_encoder.joblib")
    joblib.dump(model, model_file)
    joblib.dump(le, encoder_file)

    print(f" Saved model: {model_file}")
    print(f" Saved encoder: {encoder_file}")
    print("=" * 60)

if __name__ == "__main__":
    train_classifier()
