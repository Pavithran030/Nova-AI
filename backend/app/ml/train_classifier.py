import os
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay
import joblib

# Import from Nova's synthetic data generator
from app.utils.synthetic_data import generate_transaction_batch

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODEL_DIR, exist_ok=True)

def train_root_cause_classifier():
    """Train the root-cause classifier on synthetic data.
    
    Outputs:
      - root_cause_model.joblib
      - root_cause_label_encoder.joblib
      - confusion_matrix.png
      - feature_importance.png
    """
    df = generate_transaction_batch(n=3000)
    X = df.drop(columns=["root_cause"])
    y = df["root_cause"]

    print("Class distribution:")
    print(y.value_counts())
    print()

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, stratify=y_enc, random_state=42
    )

    model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        objective="multi:softprob",
        eval_metric="mlogloss",
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    print("\n=== Classification Report ===")
    print(classification_report(y_test, preds, target_names=le.classes_))

    # Confusion matrix (save static plot)
    cm = confusion_matrix(y_test, preds)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=le.classes_)
    fig, ax = plt.subplots(figsize=(10, 8))
    disp.plot(ax=ax, cmap="Blues", xticks_rotation=45)
    ax.set_title("Nova — Root-Cause Classifier: Confusion Matrix")
    plt.tight_layout()
    plt.savefig(os.path.join(MODEL_DIR, "confusion_matrix.png"), dpi=150)
    print("Saved confusion_matrix.png")

    # Feature importance plot
    importances = model.feature_importances_
    sorted_idx = np.argsort(importances)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(range(len(sorted_idx)), importances[sorted_idx])
    ax.set_yticks(range(len(sorted_idx)))
    ax.set_yticklabels(X.columns[sorted_idx])
    ax.set_title("Nova — Root-Cause Classifier: Feature Importance")
    ax.set_xlabel("Importance")
    plt.tight_layout()
    plt.savefig(os.path.join(MODEL_DIR, "feature_importance.png"), dpi=150)
    print("Saved feature_importance.png")

    # Save models
    joblib.dump(model, os.path.join(MODEL_DIR, "root_cause_model.joblib"))
    joblib.dump(le, os.path.join(MODEL_DIR, "root_cause_label_encoder.joblib"))
    print(f"\nModels successfully saved to {MODEL_DIR}/")

    return model, le

if __name__ == "__main__":
    train_root_cause_classifier()
