"""
Phase 1: Gut & Overall Health Checkup App
- PSS-10 validated stress questionnaire
- Stroop Test (behavioral stress/cognitive load measurement)
- Basic info + gut symptom questions
- Saves baseline result per person (by name/ID) to a local JSON file

"""

import streamlit as st
import json
import os
import time
import random
from datetime import datetime
 
DATA_FILE = "data/baseline_records.json"
 
 
# ---------------- STORAGE HELPERS ----------------
 
def load_records():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)
 
 
def save_record(user_id, record):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    records = load_records()
    records[user_id] = record
    with open(DATA_FILE, "w") as f:
        json.dump(records, f, indent=2)
 
 
# ---------------- PSS-10 LOGIC ----------------
 
PSS10_QUESTIONS = [
    "Been upset because of something that happened unexpectedly?",
    "Felt that you were unable to control the important things in your life?",
    "Felt nervous and stressed?",
    "Felt confident about your ability to handle your personal problems?",
    "Felt that things were going your way?",
    "Found that you could not cope with all the things you had to do?",
    "Been able to control irritations in your life?",
    "Felt that you were on top of things?",
    "Been angered because of things outside of your control?",
    "Felt difficulties were piling up so high that you could not overcome them?",
]
 
# Indices (0-based) of reverse-scored questions
REVERSE_SCORED = {3, 4, 6, 7}
 
PSS10_OPTIONS = ["Never", "Almost Never", "Sometimes", "Fairly Often", "Very Often"]
 
 
def calculate_pss10_score(answers):
    """answers: list of 10 ints (0-4). Returns total score 0-40."""
    total = 0
    for i, ans in enumerate(answers):
        if i in REVERSE_SCORED:
            total += (4 - ans)
        else:
            total += ans
    return total
 
 
def interpret_pss10(score):
    if score <= 13:
        return "Low Stress"
    elif score <= 26:
        return "Moderate Stress"
    else:
        return "High Stress"
 
 
# ---------------- STROOP TEST LOGIC ----------------
 
STROOP_COLORS = {
    "RED": "#FF4B4B",
    "GREEN": "#2ECC71",
    "BLUE": "#3498DB",
    "YELLOW": "#F1C40F",
}
 
 
def generate_stroop_round():
    """Returns (word, ink_color_name, ink_color_hex) where word != ink_color sometimes (interference)."""
    word = random.choice(list(STROOP_COLORS.keys()))
    ink_color_name = random.choice(list(STROOP_COLORS.keys()))
    return word, ink_color_name, STROOP_COLORS[ink_color_name]
 
 
def interpret_stroop(avg_reaction_time, accuracy_pct):
    """Simple heuristic scoring based on reaction time + accuracy."""
    if avg_reaction_time < 1.2 and accuracy_pct >= 85:
        return "Low Cognitive Stress", 10
    elif avg_reaction_time < 2.0 and accuracy_pct >= 70:
        return "Moderate Cognitive Stress", 20
    else:
        return "High Cognitive Stress", 30
 
 
# ---------------- COMBINED GUT HEALTH SCORE ----------------
 
GUT_SYMPTOM_POINTS = {
    "bloating": {"Never": 0, "Rarely": 3, "Sometimes": 6, "Often": 9, "Daily": 12},
    "abdominal_pain": {"Never": 0, "Rarely": 3, "Sometimes": 6, "Often": 9, "Daily": 12},
    "bowel_regularity": {"Very Regular": 0, "Regular": 3, "Somewhat Regular": 6, "Irregular": 9, "Very Irregular": 12},
    "stool_consistency": {"Normal": 0, "Varies a lot": 4, "Hard/Constipated": 8, "Loose/Diarrhea": 8},
}
 
 
def calculate_gut_health_score(bloating, abdominal_pain, bowel_regularity, stool_consistency,
                                 pss_score, stroop_points, bmi):
    """
    Combines gut symptoms + stress (PSS-10) + cognitive stress (Stroop) + BMI
    into one overall Gut Health Score out of 100.
    Higher score = WORSE gut health (like a risk score). We'll flip it for display.
    """
    symptom_points = (
        GUT_SYMPTOM_POINTS["bloating"][bloating]
        + GUT_SYMPTOM_POINTS["abdominal_pain"][abdominal_pain]
        + GUT_SYMPTOM_POINTS["bowel_regularity"][bowel_regularity]
        + GUT_SYMPTOM_POINTS["stool_consistency"][stool_consistency]
    )  # max 48
 
    # PSS-10 max is 40 -> scale to max 30 points contribution
    stress_points = (pss_score / 40) * 30  # max 30
 
    # Stroop contributes directly, already scaled 10/20/30 -> use as-is, max 30... 
    # but to keep total near 100, scale down slightly
    cognitive_points = (stroop_points / 30) * 15  # max 15
 
    # BMI: mild extra points if outside healthy range (18.5-24.9)
    if bmi < 18.5 or bmi > 24.9:
        bmi_points = 7
    else:
        bmi_points = 0
 
    total_risk_points = symptom_points + stress_points + cognitive_points + bmi_points
    max_possible = 48 + 30 + 15 + 7  # = 100
 
    risk_score = round((total_risk_points / max_possible) * 100)
    health_score = 100 - risk_score  # flip: higher = better health
 
    if health_score >= 75:
        category = "Good Gut Health"
    elif health_score >= 50:
        category = "Moderate Gut Health — room for improvement"
    else:
        category = "Poor Gut Health — lifestyle changes recommended"
 
    return health_score, category
 
 
# ---------------- STREAMLIT APP ----------------
 
st.set_page_config(page_title="Gut & Health Checkup", layout="centered")
st.title("🩺 Gut & Overall Health Checkup — Phase 1")
st.write("This baseline checkup combines a validated stress scale (PSS-10), "
         "a behavioral stress test (Stroop Test), and gut health questions "
         "to build your starting health profile.")
 
# Session state setup
if "stroop_round" not in st.session_state:
    st.session_state.stroop_round = 0
if "stroop_times" not in st.session_state:
    st.session_state.stroop_times = []
if "stroop_correct" not in st.session_state:
    st.session_state.stroop_correct = 0
if "stroop_start_time" not in st.session_state:
    st.session_state.stroop_start_time = None
if "current_stroop" not in st.session_state:
    st.session_state.current_stroop = generate_stroop_round()
if "stroop_done" not in st.session_state:
    st.session_state.stroop_done = False
 
TOTAL_STROOP_ROUNDS = 10
 
# ---------------- SECTION 1: Basic Info ----------------
st.header("1. Basic Information")
user_id = st.text_input("Your Name / Unique ID (used to save your record)")
age = st.number_input("Age", 10, 100, 25)
gender = st.selectbox("Gender", ["Male", "Female", "Other"])
weight = st.number_input("Weight (kg)", 30, 200, 65)
height = st.number_input("Height (cm)", 100, 220, 165)
bmi = round(weight / ((height / 100) ** 2), 1)
st.write(f"Calculated BMI: **{bmi}**")
 
# ---------------- SECTION 2: Gut Symptoms ----------------
st.header("2. Gut Symptoms (Last 2 Weeks)")
bloating = st.select_slider("Bloating frequency", ["Never", "Rarely", "Sometimes", "Often", "Daily"])
bowel_regularity = st.select_slider("Bowel movement regularity", ["Very Irregular", "Irregular", "Somewhat Regular", "Regular", "Very Regular"])
abdominal_pain = st.select_slider("Abdominal pain/discomfort frequency", ["Never", "Rarely", "Sometimes", "Often", "Daily"])
stool_consistency = st.selectbox("Typical stool consistency", ["Hard/Constipated", "Normal", "Loose/Diarrhea", "Varies a lot"])
 
# ---------------- SECTION 3: PSS-10 ----------------
st.header("3. Perceived Stress Scale (PSS-10)")
st.caption("In the last month, how often have you...")
pss_answers = []
for i, q in enumerate(PSS10_QUESTIONS):
    ans = st.select_slider(f"{i+1}. {q}", options=PSS10_OPTIONS, key=f"pss_{i}")
    pss_answers.append(PSS10_OPTIONS.index(ans))
 
# ---------------- SECTION 4: Stroop Test ----------------
st.header("4. Stroop Test (Behavioral Stress Measurement)")
st.write("Click the button matching the **INK COLOR** of the word, not what the word says. "
         f"Complete {TOTAL_STROOP_ROUNDS} rounds.")
 
if st.session_state.stroop_round < TOTAL_STROOP_ROUNDS:
    word, ink_name, ink_hex = st.session_state.current_stroop
 
    st.markdown(
        f"<h1 style='text-align: center; color: {ink_hex};'>{word}</h1>",
        unsafe_allow_html=True
    )
 
    if st.session_state.stroop_start_time is None:
        st.session_state.stroop_start_time = time.time()
 
    cols = st.columns(4)
    color_names = list(STROOP_COLORS.keys())
    for idx, cname in enumerate(color_names):
        if cols[idx].button(cname, key=f"stroop_btn_{st.session_state.stroop_round}_{cname}"):
            reaction_time = time.time() - st.session_state.stroop_start_time
            st.session_state.stroop_times.append(reaction_time)
            if cname == ink_name:
                st.session_state.stroop_correct += 1
            st.session_state.stroop_round += 1
            st.session_state.stroop_start_time = None
            st.session_state.current_stroop = generate_stroop_round()
            st.rerun()
 
    st.progress(st.session_state.stroop_round / TOTAL_STROOP_ROUNDS)
else:
    st.session_state.stroop_done = True
    avg_rt = sum(st.session_state.stroop_times) / len(st.session_state.stroop_times)
    accuracy = (st.session_state.stroop_correct / TOTAL_STROOP_ROUNDS) * 100
    st.success(f"Stroop Test complete! Avg reaction time: {avg_rt:.2f}s | Accuracy: {accuracy:.0f}%")
 
# ---------------- SUBMIT ----------------
st.header("5. Submit Checkup")
 
if st.button("Calculate My Health Baseline"):
    if not user_id:
        st.error("Please enter your Name/ID before submitting.")
    elif not st.session_state.stroop_done:
        st.error("Please complete the Stroop Test first (Section 4) before submitting.")
    else:
        pss_score = calculate_pss10_score(pss_answers)
        pss_result = interpret_pss10(pss_score)
 
        avg_rt = sum(st.session_state.stroop_times) / len(st.session_state.stroop_times)
        accuracy = (st.session_state.stroop_correct / TOTAL_STROOP_ROUNDS) * 100
        stroop_result, stroop_points = interpret_stroop(avg_rt, accuracy)
 
        gut_health_score, gut_health_category = calculate_gut_health_score(
            bloating, abdominal_pain, bowel_regularity, stool_consistency,
            pss_score, stroop_points, bmi
        )
 
        record = {
            "user_id": user_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "age": age,
            "gender": gender,
            "bmi": bmi,
            "bloating": bloating,
            "bowel_regularity": bowel_regularity,
            "abdominal_pain": abdominal_pain,
            "stool_consistency": stool_consistency,
            "pss10_score": pss_score,
            "pss10_result": pss_result,
            "stroop_avg_reaction_time": round(avg_rt, 2),
            "stroop_accuracy_pct": accuracy,
            "stroop_result": stroop_result,
            "gut_health_score": gut_health_score,
            "gut_health_category": gut_health_category,
        }
 
        save_record(user_id, record)
 
        st.balloons()
 
        # ---- Styled Result Card ----
        if gut_health_score >= 75:
            color = "#2ECC71"
            bg_color = "#EAFBF1"
            emoji = "🟢"
        elif gut_health_score >= 50:
            color = "#F39C12"
            bg_color = "#FEF6E7"
            emoji = "🟡"
        else:
            color = "#E74C3C"
            bg_color = "#FDEDEC"
            emoji = "🔴"
 
        st.markdown(
            f"""
            <div style="
                background-color: {bg_color};
                border: 2px solid {color};
                border-radius: 16px;
                padding: 30px;
                text-align: center;
                margin: 20px 0;
            ">
                <p style="font-size: 20px; color: #555; margin-bottom: 5px;">
                    {emoji} YOUR GUT HEALTH RESULT
                </p>
                <p style="font-size: 64px; font-weight: 800; color: {color}; margin: 10px 0;">
                    {gut_health_score}<span style="font-size: 28px; color: #888;"> / 100</span>
                </p>
                <p style="font-size: 28px; font-weight: 700; color: {color}; margin-top: 0;">
                    {gut_health_category}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
 
        st.markdown("### 🔍 What's Driving This Result")
        insights = []
        if bloating in ["Often", "Daily"]:
            insights.append("Frequent bloating is contributing negatively to your score")
        if abdominal_pain in ["Often", "Daily"]:
            insights.append("Frequent abdominal pain is a significant factor")
        if bowel_regularity in ["Irregular", "Very Irregular"]:
            insights.append("Irregular bowel movements are affecting your score")
        if pss_result == "High Stress":
            insights.append("Your stress level (PSS-10) is high, a known driver of gut symptoms")
        if stroop_result == "High Cognitive Stress":
            insights.append("Your Stroop test suggests elevated cognitive stress")
        if bmi < 18.5 or bmi > 24.9:
            insights.append("Your BMI is outside the typical healthy range (18.5–24.9)")
        if not insights:
            insights.append("No major risk factors detected — keep up your current habits!")
 
        for line in insights:
            st.markdown(
                f"""<div style="
                    background-color: #F8F9FA;
                    border-left: 4px solid {color};
                    padding: 12px 18px;
                    border-radius: 6px;
                    margin-bottom: 8px;
                    font-size: 16px;
                ">{line}</div>""",
                unsafe_allow_html=True
            )
 
        # ---- Sub-scores as a clean row ----
        st.markdown("### 📊 Component Breakdown")
        c1, c2, c3 = st.columns(3)
        c1.metric("PSS-10 Stress", pss_result, f"Score: {pss_score}/40")
        c2.metric("Stroop Test", stroop_result, f"{avg_rt:.2f}s avg")
        c3.metric("BMI", f"{bmi}", "Healthy: 18.5–24.9")
 
        with st.expander("See full detailed data (raw record)"):
            st.json(record)
 
        st.info("💾 This baseline is now saved. In Phase 2, you'll log daily habits "
                "that get compared against this starting point.")