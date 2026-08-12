"""
Phase 3: Train the Gut Health Prediction Model

WHY SYNTHETIC DATA: We don't have enough real accumulated user data yet
(this is the "cold-start problem" in ML). So we generate realistic synthetic
data based on known relationships between lifestyle factors and gut health,
train a model on that, and can later retrain on real data as it accumulates.

HOW TO USE:
1. Place this file at: gut-health-tracker/src/train_phase3.py
2. Run: pip install scikit-learn xgboost pandas numpy joblib (if not already installed)
3. Run from project root: python src/train_phase3.py
4. This creates: models/phase3_model.pkl and models/phase3_encoder.pkl
"""

import numpy as np
import pandas as pd
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from xgboost import XGBClassifier

np.random.seed(42)

# ---------------- STEP 1: GENERATE SYNTHETIC DATASET ----------------

N_PEOPLE = 60
N_DAYS = 45

rows = []

for person_id in range(N_PEOPLE):
    # Each person has a "baseline tendency" so patterns feel realistic per-person
    base_sleep = np.random.uniform(5.5, 8.5)
    base_fiber_habit = np.random.uniform(0, 4)
    base_stress = np.random.uniform(1, 5)

    daily_history = []

    for day in range(N_DAYS):
        sleep_hours = np.clip(np.random.normal(base_sleep, 0.8), 3, 10)
        water_glasses = np.clip(np.random.normal(6, 2), 0, 15)
        fiber_servings = np.clip(np.random.normal(base_fiber_habit, 1), 0, 6)
        fried_spicy_score = np.random.choice([0, 3, 7, 12], p=[0.3, 0.3, 0.25, 0.15])
        alcohol = np.random.choice([0, 1], p=[0.85, 0.15])
        exercise_minutes = np.clip(np.random.normal(25, 20), 0, 120)
        stress_today = np.clip(np.random.normal(base_stress, 1), 1, 5)
        bloating_score = np.random.choice([0, 4, 8, 12], p=[0.4, 0.3, 0.2, 0.1])
        # 0 = Regular Night Sleep, 1 = Day Sleep (Night Shift), 2 = Irregular/Rotating
        sleep_schedule_score = np.random.choice([0, 6, 10], p=[0.75, 0.15, 0.10])

        daily_history.append({
            "sleep_hours": sleep_hours, "water_glasses": water_glasses,
            "fiber_servings": fiber_servings, "fried_spicy_score": fried_spicy_score,
            "alcohol": alcohol, "exercise_minutes": exercise_minutes,
            "stress_today": stress_today, "bloating_score": bloating_score,
            "sleep_schedule_score": sleep_schedule_score,
        })

    df_person = pd.DataFrame(daily_history)

    # Rolling 3-day averages as FEATURES (this is what the model will actually use)
    for col in df_person.columns:
        df_person[f"{col}_roll3"] = df_person[col].rolling(window=3, min_periods=1).mean()

    df_person["person_id"] = person_id
    rows.append(df_person)

full_df = pd.concat(rows, ignore_index=True)

# ---------------- BALANCED TARGET USING QUANTILE BINNING ----------------
# Instead of fixed thresholds (which caused class imbalance), we bucket
# risk scores into equal-sized groups based on the actual data distribution.
# This guarantees roughly balanced Good/Moderate/Poor classes.

feature_cols_temp = [c for c in full_df.columns if c.endswith("_roll3")]

risk_points_all = (
    (8 - full_df["sleep_hours_roll3"]).clip(lower=0) * 4
    + (6 - full_df["water_glasses_roll3"]).clip(lower=0) * 2
    + (3 - full_df["fiber_servings_roll3"]).clip(lower=0) * 5
    + full_df["fried_spicy_score_roll3"] * 1.2
    + full_df["alcohol_roll3"] * 15
    + (20 - full_df["exercise_minutes_roll3"]).clip(lower=0) * 0.5
    + full_df["stress_today_roll3"] * 6
    + full_df["bloating_score_roll3"] * 1.5
    + full_df["sleep_schedule_score_roll3"] * 1.8
    + np.random.normal(0, 8, size=len(full_df))
)

# qcut splits into 3 equal-sized groups based on actual score distribution
full_df["target_today"] = pd.qcut(risk_points_all, q=3, labels=["Good", "Moderate", "Poor"])

# Shift target by 1 day per person: today's rolling averages predict TOMORROW's category
full_df["target"] = full_df.groupby("person_id")["target_today"].shift(-1)
full_df = full_df.dropna(subset=["target"])  # drop last day per person (no "tomorrow" to predict)

print(f"Generated dataset: {full_df.shape[0]} rows across {N_PEOPLE} simulated people")
print(full_df["target"].value_counts())

# ---------------- STEP 2: PREPARE FEATURES ----------------

feature_cols = feature_cols_temp
X = full_df[feature_cols]
y = full_df["target"]

le = LabelEncoder()
y_encoded = le.fit_transform(y)  # Good/Moderate/Poor -> 0/1/2

X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
)

# ---------------- STEP 3: TRAIN & COMPARE MODELS ----------------

models = {
    "LogisticRegression": LogisticRegression(max_iter=1000, class_weight="balanced"),
    "RandomForest": RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced"),
    "XGBoost": XGBClassifier(eval_metric="mlogloss", random_state=42),
}

best_model = None
best_acc = 0
best_name = None

for name, model in models.items():
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"\n{name} -> Accuracy: {acc:.3f}")
    print(classification_report(y_test, preds, target_names=le.classes_))

    if acc > best_acc:
        best_acc = acc
        best_model = model
        best_name = name

print(f"\nBest model: {best_name} (Accuracy: {best_acc:.3f})")

# ---------------- STEP 4: FEATURE IMPORTANCE (for recommendations) ----------------

if hasattr(best_model, "feature_importances_"):
    importance_df = pd.DataFrame({
        "feature": feature_cols,
        "importance": best_model.feature_importances_
    }).sort_values("importance", ascending=False)
    print("\nFeature Importance (what drives predictions most):")
    print(importance_df)
else:
    importance_df = pd.DataFrame({"feature": feature_cols, "importance": [1] * len(feature_cols)})

# ---------------- STEP 5: SAVE EVERYTHING ----------------

os.makedirs("models", exist_ok=True)
joblib.dump(best_model, "models/phase3_model.pkl")
joblib.dump(le, "models/phase3_encoder.pkl")
joblib.dump(feature_cols, "models/phase3_features.pkl")
importance_df.to_csv("models/phase3_feature_importance.csv", index=False)

print("\nSaved: models/phase3_model.pkl, phase3_encoder.pkl, phase3_features.pkl")