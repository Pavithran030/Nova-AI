"""
Nova ML Pipeline — Model 1: Root-Cause Classifier

Prerequisites:
    python data_generator.py     # writes data/*.csv
    python validate_dataset.py   # confirms the leakage/balance gate passes

Procedure implemented here (see TRAINING_GUIDE.md for the full walkthrough):
    1. Load pre-generated train/holdout CSVs
    2. Baseline sanity check (DummyClassifier)
    3. Cross-validated hyperparameter search (scored on macro-F1)
    4. Refit best config with early stopping against a validation split
    5. Train-vs-validation diagnostic (overfit / underfit read)
    6. Confidence-vs-accuracy reliability curve (threshold derived empirically,
       not assumed to be the 0.70 figure from the design docs)
    7. Final evaluation on the independent holdout batch
    8. Save model + encoder + plots + metadata.json
"""

import os
import json
import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, StratifiedKFold, RandomizedSearchCV
from sklearn.preprocessing import LabelEncoder
from sklearn.dummy import DummyClassifier
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
    f1_score,
)
from xgboost import XGBClassifier
import joblib

from data_generator import TX_NUMERIC_FEATURES, TX_LABEL_COLUMN, TX_CLASSES

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)


def load_split():
    train_path = os.path.join(DATA_DIR, "transactions_train.csv")
    holdout_path = os.path.join(DATA_DIR, "transactions_holdout.csv")
    if not (os.path.exists(train_path) and os.path.exists(holdout_path)):
        raise FileNotFoundError(
            "data/*.csv not found. Run `python data_generator.py` first."
        )
    return pd.read_csv(train_path), pd.read_csv(holdout_path)


def train_classifier():
    print("=" * 60)
    print(" Nova ML Pipeline — Model 1: Root-Cause Classifier ")
    print("=" * 60)

    # 1. Load data
    train_df, holdout_df = load_split()
    print(f"\n[1/8] Loaded {len(train_df)} train rows, {len(holdout_df)} holdout rows")
    print(train_df[TX_LABEL_COLUMN].value_counts())

    X = train_df[TX_NUMERIC_FEATURES]  # customer_id is deliberately excluded
    le = LabelEncoder()
    le.fit(TX_CLASSES)  # fixed class order shared by train & holdout
    y = le.transform(train_df[TX_LABEL_COLUMN])

    X_tr, X_val, y_tr, y_val = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    # XGBoost's default objective optimizes frequency-weighted log-loss, so
    # without explicit weighting it will happily ignore rare classes if that
    # minimizes overall loss. compute_sample_weight("balanced", ...) upweights
    # rows from smaller classes so the loss actually penalizes ignoring them.
    sample_weight_tr = compute_sample_weight(class_weight="balanced", y=y_tr)

    # 2. Baseline
    print("\n[2/8] Baseline (stratified random guesser)...")
    baseline = DummyClassifier(strategy="stratified", random_state=42)
    baseline.fit(X_tr, y_tr)
    baseline_f1 = f1_score(y_val, baseline.predict(X_val), average="macro")
    print(f"  Baseline macro-F1: {baseline_f1:.3f}  (the real model must clearly beat this)")

    # 3. Hyperparameter search
    print("\n[3/8] Randomized hyperparameter search (5-fold CV, scoring=f1_macro)...")
    # Regularization floor raised (min reg_alpha/reg_lambda up, max_depth and
    # subsample/colsample capped lower) relative to the first pass — sample
    # weighting amplifies minority-class rows, which otherwise gives the
    # model more room to overfit specifically to those upweighted samples.
    param_dist = {
        "max_depth": [3, 4, 5],
        "learning_rate": [0.02, 0.03, 0.05, 0.08],
        "subsample": [0.6, 0.7, 0.8],
        "colsample_bytree": [0.6, 0.7, 0.8],
        "reg_alpha": [0.5, 1.0, 2.0, 3.0],
        "reg_lambda": [1.0, 2.0, 3.0, 4.0],
    }
    search = RandomizedSearchCV(
        XGBClassifier(
            n_estimators=300,
            objective="multi:softprob",
            eval_metric="mlogloss",
            random_state=42,
        ),
        param_distributions=param_dist,
        n_iter=20,
        scoring="f1_macro",
        cv=StratifiedKFold(5, shuffle=True, random_state=42),
        random_state=42,
        n_jobs=-1,
    )
    search.fit(X_tr, y_tr, sample_weight=sample_weight_tr)
    best_params = search.best_params_
    print(f"  Best CV macro-F1: {search.best_score_:.3f}")
    print(f"  Best params: {best_params}")

    # 4. Refit with early stopping
    print("\n[4/8] Refitting best config with early stopping against validation...")
    model = XGBClassifier(
        n_estimators=1000,
        **best_params,
        objective="multi:softprob",
        eval_metric="mlogloss",
        early_stopping_rounds=30,
        random_state=42,
    )
    model.fit(
        X_tr, y_tr,
        sample_weight=sample_weight_tr,
        eval_set=[(X_tr, y_tr), (X_val, y_val)],
        verbose=False,
    )
    print(f"  Stopped at iteration {model.best_iteration} (of 1000 max)")

    # 5. Train vs val diagnostics
    print("\n[5/8] Train vs validation performance (overfit/underfit check)...")
    train_preds = model.predict(X_tr)
    val_preds = model.predict(X_val)
    train_f1 = f1_score(y_tr, train_preds, average="macro")
    val_f1 = f1_score(y_val, val_preds, average="macro")
    print(f"  Train macro-F1: {train_f1:.3f}")
    print(f"  Val   macro-F1: {val_f1:.3f}")
    gap = train_f1 - val_f1
    if gap > 0.15:
        print(f"  WARNING: gap of {gap:.3f} suggests OVERFITTING — add regularization.")
    elif val_f1 < baseline_f1 + 0.10:
        print("  WARNING: val F1 barely beats baseline — suggests UNDERFITTING / weak signal.")
    else:
        print("  Train/val gap looks healthy.")

    print("\nValidation classification report:")
    print(classification_report(y_val, val_preds, target_names=le.classes_, zero_division=0))

    # 6. Confidence-vs-accuracy reliability curve (empirically derived, not
    # assumed) — a fixed 0.70 figure from a design doc has no reason to fit
    # this specific model's actual confidence distribution, especially for
    # a 6-class problem where random-guess is ~0.167, not ~0.5.
    print("\n[6/8] Confidence-vs-accuracy reliability curve on validation set...")
    val_probas = model.predict_proba(X_val)
    val_conf = val_probas.max(axis=1)
    overall_acc = float((val_preds == y_val).mean())
    print(f"  Confidence distribution: min={val_conf.min():.3f}  median={np.median(val_conf):.3f}  max={val_conf.max():.3f}")
    print(f"  Overall (ungated) validation accuracy: {overall_acc:.3f}")
    print(f"\n  {'threshold':>10s} {'rows>=t':>8s} {'accuracy':>9s}")
    thresholds = [0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60, 0.70]
    reliability_curve = []
    recommended_threshold = None
    min_rows_for_signal = 20
    for t in thresholds:
        mask = val_conf >= t
        rows = int(mask.sum())
        if rows == 0:
            print(f"  {t:>10.2f} {0:>8d} {'n/a':>9s}")
            reliability_curve.append({"threshold": t, "rows": 0, "accuracy": None})
            continue
        acc = float((val_preds[mask] == y_val[mask]).mean())
        print(f"  {t:>10.2f} {rows:>8d} {acc:>9.3f}")
        reliability_curve.append({"threshold": t, "rows": rows, "accuracy": round(acc, 4)})
        if recommended_threshold is None and rows >= min_rows_for_signal and acc >= overall_acc + 0.05:
            recommended_threshold = t

    if recommended_threshold is not None:
        print(
            f"\n  Recommended operating threshold: {recommended_threshold:.2f} "
            f"(lowest threshold with >= {min_rows_for_signal} rows and a real "
            f"accuracy lift over the ungated {overall_acc:.3f})"
        )
    else:
        print(
            f"\n  No threshold in {thresholds} gives both >= {min_rows_for_signal} "
            "rows and a clear accuracy lift. The fixed 0.70 figure does not fit "
            "this model's real confidence distribution — do not wire an "
            "escalation gate to 0.70 as-is."
        )

    # 7. Final holdout evaluation
    print("\n[7/8] Final evaluation on the independent holdout batch (different seed)...")
    X_hold = holdout_df[TX_NUMERIC_FEATURES]
    y_hold = le.transform(holdout_df[TX_LABEL_COLUMN])
    hold_preds = model.predict(X_hold)
    hold_f1 = f1_score(y_hold, hold_preds, average="macro")
    print(f"  Holdout macro-F1: {hold_f1:.3f}  (val was {val_f1:.3f})")
    if val_f1 - hold_f1 > 0.10:
        print("  WARNING: holdout notably worse than val — likely tuned to the val split.")
    print("\nHoldout classification report:")
    print(classification_report(y_hold, hold_preds, target_names=le.classes_, zero_division=0))

    # 8. Save artifacts + metadata
    print("\n[8/8] Saving model, plots, and metadata...")

    cm = confusion_matrix(y_hold, hold_preds)
    fig, ax = plt.subplots(figsize=(9, 7))
    ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=le.classes_).plot(
        ax=ax, cmap="Blues", xticks_rotation=45
    )
    ax.set_title("Nova — Root-Cause Classifier: Holdout Confusion Matrix")
    plt.tight_layout()
    plt.savefig(os.path.join(ARTIFACTS_DIR, "confusion_matrix.png"), dpi=150)
    plt.close()

    importances = model.feature_importances_
    order = np.argsort(importances)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(range(len(order)), importances[order], color="#3B6CF5")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(np.array(TX_NUMERIC_FEATURES)[order])
    ax.set_title("Nova — Root-Cause Classifier: Feature Importance")
    plt.tight_layout()
    plt.savefig(os.path.join(ARTIFACTS_DIR, "feature_importance.png"), dpi=150)
    plt.close()

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(val_conf, bins=20, color="#12875A", edgecolor="black", alpha=0.7)
    if recommended_threshold is not None:
        ax.axvline(
            recommended_threshold, color="#D13438", linestyle="--", linewidth=2,
            label=f"Recommended threshold ({recommended_threshold:.2f})",
        )
        ax.legend()
        ax.set_title("Nova — Validation Confidence Distribution")
    else:
        ax.set_title(
            "Nova — Validation Confidence Distribution\n"
            "(no reliable threshold found — see reliability_curve in metadata)"
        )
    plt.tight_layout()
    plt.savefig(os.path.join(ARTIFACTS_DIR, "confidence_distribution.png"), dpi=150)
    plt.close()

    joblib.dump(model, os.path.join(ARTIFACTS_DIR, "root_cause_model.joblib"))
    joblib.dump(le, os.path.join(ARTIFACTS_DIR, "root_cause_encoder.joblib"))

    metadata = {
        "trained_at": datetime.datetime.now().isoformat(),
        "model_type": "XGBClassifier",
        "classes": list(le.classes_),
        "features": TX_NUMERIC_FEATURES,
        "n_train": int(len(X_tr)),
        "n_val": int(len(X_val)),
        "n_holdout": int(len(X_hold)),
        "best_params": best_params,
        "best_iteration": int(model.best_iteration),
        "baseline_macro_f1": round(float(baseline_f1), 4),
        "train_macro_f1": round(float(train_f1), 4),
        "val_macro_f1": round(float(val_f1), 4),
        "holdout_macro_f1": round(float(hold_f1), 4),
        "reliability_curve": reliability_curve,
        "recommended_confidence_threshold": recommended_threshold,
    }
    with open(os.path.join(ARTIFACTS_DIR, "classifier_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"  Saved model, encoder, plots, and classifier_metadata.json to {ARTIFACTS_DIR}/")
    print("=" * 60)
    return model, le, metadata


if __name__ == "__main__":
    train_classifier()
