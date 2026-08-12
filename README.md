# Gut & Overall Health Tracker

An end-to-end personal health tracking system that combines validated psychological assessments, behavioral testing, daily lifestyle logging, and a machine learning model to predict and improve gut health over time.
**Live Demo:** [Try it here](https://gut-health-tracker.streamlit.app/)

## Problem Statement

Most gut health issues (bloating, irregularity, discomfort) are strongly linked to lifestyle factors — sleep, stress, diet, hydration, and activity — but people rarely track these factors consistently enough to spot patterns. This project builds a system that establishes a health baseline, tracks daily habits over time, and uses machine learning to predict trends and give personalized, actionable recommendations.

## System Architecture — 3 Phases

### Phase 1: Baseline Health Checkup (Rule-Based)
A one-time assessment combining:
- **Gut symptom questionnaire** (bloating, bowel regularity, abdominal pain, stool consistency)
- **PSS-10 (Perceived Stress Scale)** — a validated 10-question clinical stress assessment (Cohen, Kamarck & Mermelstein, 1983), correctly reverse-scored per the published methodology

- **Stroop Test** — an interactive behavioral test measuring cognitive/stress interference via reaction time and accuracy, rather than relying on self-reported stress alone
- Combines all of the above into a single **Gut Health Score (0-100)**

### Phase 2: Daily Lifestyle Logging (Rule-Based, Time-Series)
A quick daily form tracking sleep (including sleep **schedule type**, since shift/irregular sleep disrupts circadian rhythm independent of total hours), hydration, fiber intake, fried/spicy food, alcohol, exercise, stress, and symptoms.
Each day is scored and stored per user, building a personal time-series history.
A trends dashboard visualizes daily scores and a 3-day rolling average over time.

### Phase 3: ML-Based Prediction & Recommendations
Using the accumulated daily logs, a trained classification model predicts the user's likely gut health category 
**tomorrow** (Good / Moderate / Poor) based on their 3-day rolling average habits, and generates personalized recommendations ranked by feature importance.

**Note on training data:** Real accumulated user history is limited when a product is new (the "cold-start problem" in ML). To address this, the model is trained on synthetic data that encodes realistic relationships from gut-health research (stress, fiber, sleep, and alcohol as key modifiable risk factors), with added noise for realism. As real user data accumulates, the model can be retrained on actual logged data for improved personalization.

## Model Results (Phase 3)

Model	        Accuracy	Notes
Logistic Regression	58%	Best overall; balanced across all 3 classes
Random Forest	56%	Similar performance
XGBoost	53%	Slightly lower on this dataset size

**On class balancing:** An earlier version of this model showed 66% accuracy, but this was misleading — the model was mostly predicting the majority class ("Moderate") due to class imbalance in the raw thresholds. After rebalancing classes using quantile-based bucketing, accuracy dropped to 58%, but recall for "Good" and "Poor" categories improved substantially (31%→73% and 39%→64% respectively) — meaning the model became genuinely more useful despite the lower headline accuracy number. This trade-off between raw accuracy and per-class usefulness is a well-known challenge in imbalanced classification.

## Screenshots

 ![Baseline Result](screenshots/baseline_result.png)

 ![Daily Log](screenshots/daily_log.png)

 ![Trends Chart](screenshots/trends_chart.png)

 ![Prediction](screenshots/prediction.png)
 


## Tech Stack

- **Language:** Python
- **Frontend/App:** Streamlit
- **ML:** scikit-learn, XGBoost, joblib
- **Data:** pandas, numpy
- **Storage:** JSON-based local storage (per-user baseline, daily logs, and login credentials)

## Project Structure

```
gut-health-tracker/
├── app/
│   └── health_checkup_app.py    # Full Streamlit app (all 4 pages)
├── src/
│   └── train_phase3.py          # Synthetic data generation + model training
├── models/
│   ├── phase3_model.pkl
│   ├── phase3_encoder.pkl
│   ├── phase3_features.pkl
│   └── phase3_feature_importance.csv
├── data/                         # Created automatically at runtime
├── requirements.txt
└── README.md
```

## How to Run Locally

1. Clone this repository
```bash
git clone https://github.com/persy-sagar/gut-health-tracker.git
cd gut-health-tracker
```

2. Create a virtual environment and install dependencies
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

3. (Optional) Retrain the Phase 3 model
```bash
python src/train_phase3.py
```

4. Run the app
```bash
streamlit run app/health_checkup_app.py
```

## Authentication

Users log in with a phone number and a 4-digit PIN. This is a lightweight identity system for this demo — **not real SMS OTP verification**, which requires a paid gateway service (Twilio, MSG91, etc.) and backend infrastructure beyond a free Streamlit deployment. This is a known, intentional limitation.

## Known Limitations & Future Improvements

- PINs are currently stored as plain text; production apps should hash credentials
- Real OTP-based phone verification would replace the current PIN system
- The Phase 3 model is trained on synthetic data; retraining on real accumulated user data would improve personalization and accuracy over time
- A "days to recover" feature (estimating how many days of improved habits would shift someone from Poor/Moderate to Good) is a planned Phase 4 extension
- Class imbalance remains a challenge for the "Moderate" category specifically, which is inherently the hardest to distinguish from its neighbors

## Key Learnings

- Building a system that must work with little-to-no initial data (cold-start  problem) requires a rule-based foundation before ML becomes viable
- Class imbalance can make accuracy numbers misleading; recall per class often tells a more honest story
- Combining validated psychometric tools (PSS-10) with behavioral measurement (Stroop Test) produces more defensible results than simple self-rated sliders