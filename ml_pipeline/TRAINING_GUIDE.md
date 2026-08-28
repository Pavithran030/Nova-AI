# Nova ML Training Guide

This is the complete, step-by-step procedure for building both Nova models
from scratch: the 6-class root-cause classifier and the B2B payment
probability scorer. Follow it in order — each stage gates the next one.

---

## 0. Prerequisites

```bash
cd ml_pipeline
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

---

## 1. Generate the synthetic datasets

```bash
python data_generator.py
```

This writes four files to `ml_pipeline/data/`:

| File | Purpose |
|---|---|
| `transactions_train.csv` | Train/val split source for the classifier (seed 42) |
| `transactions_holdout.csv` | Independent generalization check (seed 2024) |
| `invoices_train.csv` | Train/val split source for the scorer (seed 42) |
| `invoices_holdout.csv` | Independent generalization check (seed 2024) |

**Why two CSVs per entity, not one:** the holdout batch is generated with a
*different random seed* and is never touched during training or
hyperparameter tuning. It's the closest proxy we have to "real, unseen
data" in the absence of an actual production dataset. If a model's holdout
score is much worse than its validation score, that gap itself is the
signal that something was tuned to the validation split rather than
learned genuinely.

Expected output: a class-distribution printout for both datasets. Root
causes should be imbalanced but no class should be empty; `paid` should be
roughly balanced-ish but not 50/50 (real collections data skews toward
payment).

---

## 2. Run the validation gate — do not skip this

```bash
python validate_dataset.py
```

This checks four things, in order:

1. **Class balance** — flags any class under ~2% of the data.
2. **Single-feature leakage smoke test** — trains a depth-1 decision stump
   on *each feature alone*. If any single feature crosses ~90% accuracy
   against a 6-class label by itself, that feature is a disguised copy of
   the label (leakage), not a genuine predictor.
3. **Mutual information** — reports how much information each feature
   carries about the label. Healthy signal is spread across several
   features. One feature dominating by 3x+ over the next is a red flag.
4. **Duplicate rows** — exact duplicates artificially inflate apparent
   performance.

**Gate rule:** if leakage is flagged, go back to `data_generator.py` and
reduce that feature's weight in the score formula (`generate_transaction_dataset`)
or increase noise, then regenerate. Do not proceed to training with a
dataset that fails this gate — every metric downstream would be
meaningless.

---

## 3. Train the root-cause classifier

```bash
python train_classifier.py
```

### What the script does, stage by stage

| Stage | What happens | Why |
|---|---|---|
| 1. Load | Reads `transactions_train.csv` / `transactions_holdout.csv` | Never re-generates in-memory — keeps train and holdout genuinely separate artifacts |
| 2. Baseline | Fits `DummyClassifier(strategy="stratified")`, records macro-F1 | Your floor. If XGBoost doesn't clearly beat this, the features/labels are broken, not the hyperparameters |
| 3. Hyperparameter search | `RandomizedSearchCV` over depth/learning-rate/subsample/regularization, 5-fold stratified CV, scored on `f1_macro` | Macro-F1 (not accuracy) so rare classes like `MANDATE_REVOKED` aren't ignored |
| 4. Refit + early stopping | Refits best config with `early_stopping_rounds=30` against a held-out validation split | Primary overfitting guard — stops adding trees once validation loss stops improving |
| 5. Train vs. val diagnostic | Prints both macro-F1 scores and flags the gap | See "Reading the diagnostics" below |
| 6. Confidence calibration | Splits validation predictions at the 0.70 threshold, reports accuracy on each side | Confirms the escalation-to-human logic actually separates reliable from unreliable predictions |
| 7. Holdout evaluation | Final, only-once check on the seed-2024 batch | The number that answers "does this generalize" |
| 8. Save artifacts | `.joblib` model + encoder, 3 plots, `classifier_metadata.json` | Versioned, auditable outputs |

### Reading the diagnostics (this is the part that teaches you something)

```
Train macro-F1: 0.XX
Val   macro-F1: 0.YY
```

| Pattern | Diagnosis | Fix |
|---|---|---|
| Train ≫ Val (gap > ~0.15) | **Overfitting** — model memorized train-set quirks | Lower `max_depth`, raise `reg_alpha`/`reg_lambda`, lower `subsample`/`colsample_bytree`; or go back and increase `label_noise_rate`/`ambiguous_frac` in the generator |
| Train ≈ Val, both low (val barely above baseline) | **Underfitting** — model isn't capturing real signal | Raise `max_depth`, lower regularization; check the leakage gate didn't force you to over-blend a genuinely useful feature |
| Train ≈ Val, both moderate-to-good (macro-F1 roughly 0.55–0.80 on this deliberately-noisy 6-class data) | **Healthy.** Do not chase 0.95+ — that would mean the leakage gate should have failed | None — proceed |
| Val ≫ Holdout (gap > ~0.10) | **Tuned to the validation split** — hyperparameter search overfit its own scoring loop | Reduce `n_iter` in the search, or increase CV folds; treat the holdout number as ground truth, not validation |

There is no single "correct" macro-F1 number to target — a perfect score
on synthetic data with intentional noise/ambiguity/label-flipping is a
red flag, not a win. What matters is: (a) clearly beats baseline, (b) the
train/val/holdout gaps are all small, (c) the confidence-threshold split
actually shows lower accuracy below 0.70 than above it.

### Outputs

```
ml_pipeline/artifacts/
├── root_cause_model.joblib
├── root_cause_encoder.joblib
├── confusion_matrix.png          (on holdout)
├── feature_importance.png
├── confidence_distribution.png
└── classifier_metadata.json      (train date, params, all F1 scores)
```

---

## 4. Train the B2B payment scorer

```bash
python train_scorer.py
```

### Key differences from the classifier

- **Primary metric is Brier score, not accuracy or even AUC.** The
  `expected_recovery_value = amount × P(payment)` formula uses the raw
  probability directly — a model that ranks invoices correctly but outputs
  badly calibrated probabilities (e.g. everything squeezed near 0.5, or
  systematically too confident) will silently distort the ranking's dollar
  values even if AUC looks fine.
- **Regularization is swept via `C`** (inverse regularization strength) in
  `LogisticRegression`, scored by validation Brier — same over/underfit
  read as the classifier: `train_brier ≪ val_brier` (numerically, brier is
  "lower is better" so watch for train Brier much *lower* than val Brier)
  means overfitting; both flat and mediocre means underfitting.
- **Coefficient sign check is mandatory, not optional.** The script prints
  every coefficient with a direction label. `customer_ontime_rate` must be
  positive; `days_overdue` and `prior_broken_promises` must be negative. A
  flipped sign means something is wrong upstream (usually a data
  generation bug) — don't ship a scorer with an unintuitive sign, even if
  its Brier score looks fine, because the audit-trail "reasoning" field
  depends on these coefficients making business sense.
- **Automatic recalibration fallback**: if validation Brier > 0.15, the
  script fits `CalibratedClassifierCV` and keeps it only if it actually
  improves the score.

### Outputs

```
ml_pipeline/artifacts/
├── payment_scorer.joblib
├── calibration_curve.png         (on holdout — should hug the diagonal)
└── scorer_metadata.json
```

---

## 5. How to know training actually succeeded (checklist)

- [ ] `validate_dataset.py` gate passed with no leakage flags
- [ ] Classifier: holdout macro-F1 clearly beats the `DummyClassifier` baseline
- [ ] Classifier: train/val/holdout macro-F1 are all within ~0.10–0.15 of each other
- [ ] Classifier: accuracy on confidence ≥ 0.70 rows is clearly higher than on < 0.70 rows
- [ ] Scorer: holdout Brier clearly beats the baseline Brier
- [ ] Scorer: train/val Brier are close (no large gap)
- [ ] Scorer: every coefficient sign matches domain intuition
- [ ] `calibration_curve.png` roughly hugs the diagonal (not systematically above/below it)
- [ ] Both `*_metadata.json` files exist and contain holdout numbers, not just validation numbers

If every box is checked, you have two real, evaluated models — not just
two `.joblib` files that happen to exist.

---

## 6. What's deliberately *not* in this guide yet

Wiring these trained artifacts into the live FastAPI backend
(`backend/app/services/classifier.py`, `scorer.py`) — loading the model as
a singleton, making the rule-based first pass hand off to the ML model only
for ambiguous/unmapped error codes, and making the 0.70 threshold actually
branch to human escalation in the policy engine — is the next phase, kept
separate on purpose so dataset/model quality isn't muddled with
integration bugs. Come back to this guide once the checklist above is
green.
