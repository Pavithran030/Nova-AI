"""
Nova ML Pipeline — Dataset validation gate.

Run this BEFORE training anything. It checks for the specific failure modes
that cause a synthetic dataset to produce an overfit / hallucinating model:

  1. Class balance          -> is any class too rare to learn or too dominant?
  2. Leakage smoke test     -> does any single feature alone predict the label?
  3. Mutual information     -> is signal spread across features, or is one
                                feature suspiciously carrying everything?
  4. Duplicate rows         -> exact dupes inflate apparent performance.

Reads data/*.csv (the same files train_classifier.py / train_scorer.py use)
rather than regenerating the dataset in-memory, so this always validates
exactly what training will see — no risk of the two drifting apart if a
generation parameter changes in one place and not the other.

Usage:
    python data_generator.py   # first, if data/*.csv doesn't exist yet
    python validate_dataset.py
"""

import os

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.feature_selection import mutual_info_classif
from sklearn.preprocessing import LabelEncoder

from data_generator import (
    TX_ID_COLUMNS,
    TX_NUMERIC_FEATURES,
    TX_LABEL_COLUMN,
    INV_ID_COLUMNS,
    INV_NUMERIC_FEATURES,
    INV_LABEL_COLUMN,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def class_balance_report(df: pd.DataFrame, label_col: str) -> None:
    print("\n--- Class balance ---")
    counts = df[label_col].value_counts(normalize=True) * 100
    print((counts.round(1)).astype(str) + "%")
    minority = counts.min()
    if minority < 2:
        print(
            f"  Smallest class is {minority:.1f}% of data -> use class_weight "
            "/ scale_pos_weight during training, do not ignore it."
        )
    # "Dominant" is relative to how many classes there are: 50% is balanced
    # for a binary label but heavily skewed for a 6-class one. Flag a class
    # at roughly 2x+ its fair share.
    n_classes = df[label_col].nunique()
    fair_share = 100 / n_classes
    majority = counts.max()
    if majority > 2 * fair_share and majority > 30:
        print(
            f"  '{counts.idxmax()}' is {majority:.1f}% of data (fair share "
            f"would be {fair_share:.1f}%) -> one class is crowding out the "
            "rest. Check that class's score formula in data_generator.py for "
            "an unbounded/over-weighted term before training — class_weight "
            "alone won't fix a generator that's this skewed relative to intent."
        )


def leakage_smoke_test(
    df: pd.DataFrame, feature_cols, label_col: str, threshold: float = 0.90
):
    """A decision stump (depth-1 tree) trained on ONE feature at a time.
    If any single feature alone crosses `threshold` accuracy against a
    6-8 class label, that feature is leaking the label — go back to the
    generator and blend/noise it more."""
    print("\n--- Single-feature leakage smoke test ---")
    y = LabelEncoder().fit_transform(df[label_col])
    leaks = []
    for col in feature_cols:
        col_values = df[[col]].copy()
        col_values[col] = col_values[col].fillna(col_values[col].median())
        X_train, X_test, y_train, y_test = train_test_split(
            col_values, y, test_size=0.3, random_state=0, stratify=y
        )
        stump = DecisionTreeClassifier(max_depth=1, random_state=0)
        stump.fit(X_train, y_train)
        acc = stump.score(X_test, y_test)
        flag = "  <-- POSSIBLE LEAKAGE" if acc >= threshold else ""
        print(f"  {col:35s} single-feature accuracy = {acc:.3f}{flag}")
        if acc >= threshold:
            leaks.append(col)
    if not leaks:
        print("  No single feature independently predicts the label — good.")
    return leaks


def mutual_information_report(df: pd.DataFrame, feature_cols, label_col: str):
    print("\n--- Mutual information (feature vs label) ---")
    y = LabelEncoder().fit_transform(df[label_col])
    X = df[feature_cols].copy()
    X = X.fillna(X.median(numeric_only=True))
    mi = mutual_info_classif(X, y, random_state=0)
    report = pd.Series(mi, index=feature_cols).sort_values(ascending=False)
    print(report.round(3).to_string())
    dominant = report.iloc[0]
    if dominant > 3 * report.iloc[1]:
        print(
            f"  '{report.index[0]}' has much higher MI than everything else "
            "-> check it isn't a disguised copy of the label."
        )
    return report


def duplicate_check(df: pd.DataFrame, id_columns) -> None:
    print("\n--- Duplicate rows ---")
    dupes = int(df.drop(columns=id_columns).duplicated().sum())
    print(f"  {dupes} exact duplicate feature rows" + ("" if dupes == 0 else " -> investigate"))


def run_gate(df: pd.DataFrame, feature_cols, label_col: str, id_columns, name: str) -> None:
    print("\n" + "=" * 64)
    print(f" Validating: {name}  (n={len(df)}) ")
    print("=" * 64)
    class_balance_report(df, label_col)
    leakage_smoke_test(df, feature_cols, label_col)
    mutual_information_report(df, feature_cols, label_col)
    duplicate_check(df, id_columns)


def _load_csv(filename: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run `python data_generator.py` first."
        )
    return pd.read_csv(path)


if __name__ == "__main__":
    tx_df = _load_csv("transactions_train.csv")
    run_gate(tx_df, TX_NUMERIC_FEATURES, TX_LABEL_COLUMN, TX_ID_COLUMNS, "Transaction root-cause dataset")

    inv_df = _load_csv("invoices_train.csv")
    run_gate(inv_df, INV_NUMERIC_FEATURES, INV_LABEL_COLUMN, INV_ID_COLUMNS, "Invoice payment dataset")
