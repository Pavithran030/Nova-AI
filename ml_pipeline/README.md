# Nova ML Training & Development Pipeline

This folder contains the complete, standalone Machine Learning training and development pipeline for **Nova**.

---

## 📂 Folder Architecture

```
ml_pipeline/
├── data_generator.py      # Synthetic transaction & invoice dataset generators
├── train_classifier.py    # Model 1: XGBoost 8-Class Root-Cause Classifier Trainer
├── train_scorer.py        # Model 2: Logistic Regression B2B Payment Scorer Trainer
├── evaluate.py            # Model Health Check & Confidence Gating Evaluator
├── infer.py               # Inference service sample runner
├── requirements.txt       # ML Dependencies
├── artifacts/             # Output directory for binary models & plots
│   ├── root_cause_model.joblib
│   ├── root_cause_encoder.joblib
│   ├── payment_scorer.joblib
│   ├── confusion_matrix.png
│   ├── feature_importance.png
│   ├── confidence_distribution.png
│   └── calibration_curve.png
└── README.md
```

---

## 🚀 How to Run the Training Pipeline

### 1. Install ML Dependencies

```bash
cd ml_pipeline
pip install -r requirements.txt
```

### 2. Train Model 1 (Root-Cause Classifier)

```bash
python train_classifier.py
```
> Trains the XGBoost multi-class classifier on 5,000 synthetic transaction records. Exports `root_cause_model.joblib`, `root_cause_encoder.joblib`, `confusion_matrix.png`, `feature_importance.png`, and `confidence_distribution.png` into `artifacts/`.

### 3. Train Model 2 (B2B Payment Scorer)

```bash
python train_scorer.py
```
> Trains the Logistic Regression B2B payment probability scorer on 3,000 invoice records. Analyzes feature coefficients, checks Brier calibration, and exports `payment_scorer.joblib` and `calibration_curve.png` into `artifacts/`.

### 4. Run Pipeline Evaluation

```bash
python evaluate.py
```
> Evaluates both trained models on fresh test sets, checking the 70% confidence threshold gating and B2B expected-value ranking.

### 5. Run Test Inference

```bash
python infer.py
```
> Tests sample transaction diagnosis and invoice expected-value calculation using the exported `.joblib` model binaries.

---

## 🔄 Deploying Trained Models to Backend

To copy the freshly trained models directly into Nova's FastAPI backend:

```bash
# Windows PowerShell
copy artifacts\*.joblib ..\backend\app\ml\models\

# Linux / macOS
# cp artifacts/*.joblib ../backend/app/ml/models/
```
