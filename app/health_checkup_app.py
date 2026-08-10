"""
Gut & Overall Health Tracker — Full App (Phase 1 + Phase 2)

Pages:
1. Baseline Checkup (Phase 1) — one-time PSS-10 + Stroop + symptom checkup
2. Daily Log (Phase 2) — quick daily entry, stored per person over time
3. My Trends (Phase 2) — charts showing progress over time

HOW TO USE:
Replace your existing app/health_checkup_app.py with this file entirely.
Run: streamlit run app/health_checkup_app.py
"""

import streamlit as st
import json
import os
import re
import time
import random
import pandas as pd
from datetime import datetime, date

BASELINE_FILE = "data/baseline_records.json"
DAILY_LOG_FILE = "data/daily_logs.json"
USERS_FILE = "data/users.json"


# ---------------- STORAGE HELPERS ----------------

def load_json(filepath):
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r") as f:
        return json.load(f)


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def save_baseline(user_id, record):
    records = load_json(BASELINE_FILE)
    records[user_id] = record
    save_json(BASELINE_FILE, records)


def save_daily_log(user_id, log_entry):
    """Upsert logic: if today's entry exists for this user, update it. Otherwise append."""
    all_logs = load_json(DAILY_LOG_FILE)
    user_logs = all_logs.get(user_id, [])

    existing_index = None
    for i, entry in enumerate(user_logs):
        if entry["date"] == log_entry["date"]:
            existing_index = i
            break

    if existing_index is not None:
        user_logs[existing_index] = log_entry
    else:
        user_logs.append(log_entry)

    all_logs[user_id] = user_logs
    save_json(DAILY_LOG_FILE, all_logs)


def get_user_logs(user_id):
    all_logs = load_json(DAILY_LOG_FILE)
    return all_logs.get(user_id, [])


# ---------------- PHONE-BASED IDENTITY (LOGIN/SIGNUP) ----------------

def is_valid_phone(phone):
    """Basic validation: exactly 10 digits, digits only (Indian mobile format)."""
    return bool(re.fullmatch(r"\d{10}", phone))


def get_users():
    return load_json(USERS_FILE)


def create_user(phone, name, pin):
    users = get_users()
    users[phone.strip()] = {
        "name": name.strip(),
        "pin": pin.strip(),
        "created_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    save_json(USERS_FILE, users)


def verify_user(phone, pin):
    users = get_users()
    phone = phone.strip()
    pin = pin.strip()
    if phone in users and str(users[phone]["pin"]).strip() == pin:
        return users[phone]
    return None


def user_exists(phone):
    users = get_users()
    return phone in users



# ---------------- PSS-10 LOGIC (Phase 1) ----------------

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
REVERSE_SCORED = {3, 4, 6, 7}
PSS10_OPTIONS = ["Never", "Almost Never", "Sometimes", "Fairly Often", "Very Often"]


def calculate_pss10_score(answers):
    total = 0
    for i, ans in enumerate(answers):
        total += (4 - ans) if i in REVERSE_SCORED else ans
    return total


def interpret_pss10(score):
    if score <= 13:
        return "Low Stress"
    elif score <= 26:
        return "Moderate Stress"
    else:
        return "High Stress"


# ---------------- STROOP TEST LOGIC (Phase 1) ----------------

STROOP_COLORS = {"RED": "#FF4B4B", "GREEN": "#2ECC71", "BLUE": "#3498DB", "YELLOW": "#F1C40F"}


def generate_stroop_round():
    word = random.choice(list(STROOP_COLORS.keys()))
    ink_color_name = random.choice(list(STROOP_COLORS.keys()))
    return word, ink_color_name, STROOP_COLORS[ink_color_name]


def interpret_stroop(avg_reaction_time, accuracy_pct):
    if avg_reaction_time < 1.2 and accuracy_pct >= 85:
        return "Low Cognitive Stress", 10
    elif avg_reaction_time < 2.0 and accuracy_pct >= 70:
        return "Moderate Cognitive Stress", 20
    else:
        return "High Cognitive Stress", 30


# ---------------- GUT HEALTH SCORE (Phase 1 - Baseline) ----------------

GUT_SYMPTOM_POINTS = {
    "bloating": {"Never": 0, "Rarely": 3, "Sometimes": 6, "Often": 9, "Daily": 12},
    "abdominal_pain": {"Never": 0, "Rarely": 3, "Sometimes": 6, "Often": 9, "Daily": 12},
    "bowel_regularity": {"Very Regular": 0, "Regular": 3, "Somewhat Regular": 6, "Irregular": 9, "Very Irregular": 12},
    "stool_consistency": {"Normal": 0, "Varies a lot": 4, "Hard/Constipated": 8, "Loose/Diarrhea": 8},
}


def calculate_gut_health_score(bloating, abdominal_pain, bowel_regularity, stool_consistency,
                                 pss_score, stroop_points, bmi):
    symptom_points = (
        GUT_SYMPTOM_POINTS["bloating"][bloating]
        + GUT_SYMPTOM_POINTS["abdominal_pain"][abdominal_pain]
        + GUT_SYMPTOM_POINTS["bowel_regularity"][bowel_regularity]
        + GUT_SYMPTOM_POINTS["stool_consistency"][stool_consistency]
    )
    stress_points = (pss_score / 40) * 30
    cognitive_points = (stroop_points / 30) * 15
    bmi_points = 7 if (bmi < 18.5 or bmi > 24.9) else 0

    total_risk_points = symptom_points + stress_points + cognitive_points + bmi_points
    max_possible = 100
    risk_score = round((total_risk_points / max_possible) * 100)
    health_score = 100 - risk_score

    if health_score >= 75:
        category = "Good Gut Health"
    elif health_score >= 50:
        category = "Moderate Gut Health — room for improvement"
    else:
        category = "Poor Gut Health — lifestyle changes recommended"

    return health_score, category


# ---------------- DAILY LOG SCORE (Phase 2) ----------------

DAILY_POINTS = {
    "fiber_servings": {0: 15, 1: 10, 2: 5, 3: 2, 4: 0},
    "fried_spicy": {"None": 0, "Light": 3, "Moderate": 7, "Heavy": 12},
    "bloating_today": {"None": 0, "Mild": 4, "Moderate": 8, "Severe": 12},
    "sleep_quality": {"Poor": 10, "Fair": 6, "Good": 2, "Excellent": 0},
}


def calculate_daily_score(sleep_hours, sleep_quality, water_glasses, fiber_servings,
                            fried_spicy, alcohol, exercise_minutes, stress_today, bloating_today):
    points = 0
    points += DAILY_POINTS["sleep_quality"][sleep_quality]
    points += DAILY_POINTS["fried_spicy"][fried_spicy]
    points += DAILY_POINTS["bloating_today"][bloating_today]

    fiber_key = min(fiber_servings, 4)
    points += DAILY_POINTS["fiber_servings"][fiber_key]

    if water_glasses < 4:
        points += 8
    elif water_glasses < 6:
        points += 4

    if sleep_hours < 6:
        points += 8
    elif sleep_hours < 7:
        points += 3

    if alcohol == "Yes":
        points += 6

    if exercise_minutes < 15:
        points += 5

    points += (stress_today / 5) * 15

    max_possible = 15 + 12 + 12 + 15 + 8 + 8 + 6 + 5 + 15
    risk_score = round((points / max_possible) * 100)
    daily_score = max(0, 100 - risk_score)

    return daily_score


# ============================================================
# STREAMLIT APP — PAGE NAVIGATION
# ============================================================

st.set_page_config(page_title="Gut & Health Tracker", layout="centered")

# ---------------- SESSION STATE FOR LOGIN ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "phone" not in st.session_state:
    st.session_state.phone = None
if "display_name" not in st.session_state:
    st.session_state.display_name = None


# ============================================================
# LOGIN / SIGNUP GATE — shown before anything else
# ============================================================
if not st.session_state.logged_in:
    st.title("🩺 Gut & Health Tracker")
    st.write("Log in with your phone number to access your personal health profile.")

    phone_input = st.text_input("Phone Number (10 digits, no country code)", max_chars=10, key="login_phone")

    if phone_input and not is_valid_phone(phone_input):
        st.warning("Please enter a valid 10-digit phone number.")

    elif phone_input and is_valid_phone(phone_input):
        if user_exists(phone_input):
            st.success("Welcome back! Please enter your PIN to continue.")
            with st.form("login_form"):
                pin_input = st.text_input("4-digit PIN", type="password", max_chars=4, key="login_pin")
                login_submitted = st.form_submit_button("Log In")

            if login_submitted:
                user = verify_user(phone_input, pin_input)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.phone = phone_input
                    st.session_state.display_name = user["name"]
                    st.rerun()
                else:
                    st.error("Incorrect PIN. Please try again.")
        else:
            st.info("New here? Let's set up your profile.")
            with st.form("signup_form"):
                new_name = st.text_input("Your Name", key="signup_name")
                new_pin = st.text_input("Create a 4-digit PIN", type="password", max_chars=4, key="signup_pin")
                confirm_pin = st.text_input("Confirm PIN", type="password", max_chars=4, key="signup_confirm_pin")
                signup_submitted = st.form_submit_button("Create Profile")

            if signup_submitted:
                if not new_name.strip():
                    st.error("Please enter your name.")
                elif not (new_pin.isdigit() and len(new_pin) == 4):
                    st.error("PIN must be exactly 4 digits.")
                elif new_pin != confirm_pin:
                    st.error("PINs don't match.")
                else:
                    create_user(phone_input, new_name, new_pin)
                    st.session_state.logged_in = True
                    st.session_state.phone = phone_input
                    st.session_state.display_name = new_name.strip()
                    st.success("Profile created!")
                    st.rerun()

    st.caption("Note: This uses your phone number as a unique ID with a simple PIN for this demo. "
               "Production apps would verify phone numbers via SMS OTP (a paid service).")
    st.stop()  # Prevents the rest of the app from rendering until logged in


# ============================================================
# LOGGED IN — Sidebar shows who's logged in + logout option
# ============================================================
st.sidebar.success(f"👤 Logged in as: **{st.session_state.display_name}**")
st.sidebar.caption(f"Phone: {st.session_state.phone}")
if st.sidebar.button("Log Out"):
    st.session_state.logged_in = False
    st.session_state.phone = None
    st.session_state.display_name = None
    st.rerun()

page = st.sidebar.radio(
    "Navigate",
    ["🩺 Baseline Checkup (Phase 1)", "📝 Daily Log (Phase 2)", "📈 My Trends (Phase 2)"]
)

st.sidebar.markdown("---")
st.sidebar.caption("Gut & Overall Health Tracker\nPhase 1: Baseline | Phase 2: Daily Logging & Trends")

# The logged-in phone number is now used as the unique ID everywhere
user_id = st.session_state.phone


# ============================================================
# PAGE 1: BASELINE CHECKUP
# ============================================================
if page == "🩺 Baseline Checkup (Phase 1)":
    st.title("🩺 Gut & Overall Health Checkup — Baseline")
    st.write("This one-time checkup combines a validated stress scale (PSS-10), "
             "a behavioral stress test (Stroop Test), and gut health questions.")

    if "stroop_round" not in st.session_state:
        st.session_state.stroop_round = 0
        st.session_state.stroop_times = []
        st.session_state.stroop_correct = 0
        st.session_state.stroop_start_time = None
        st.session_state.current_stroop = generate_stroop_round()
        st.session_state.stroop_done = False

    TOTAL_STROOP_ROUNDS = 10

    st.header("1. Basic Information")
    st.write(f"Logged in as: **{st.session_state.display_name}**")
    user_id = st.session_state.phone
    age = st.number_input("Age", 10, 100, 25)
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
    weight = st.number_input("Weight (kg)", 30, 200, 65)
    height = st.number_input("Height (cm)", 100, 220, 165)
    bmi = round(weight / ((height / 100) ** 2), 1)
    st.write(f"Calculated BMI: **{bmi}**")

    st.header("2. Gut Symptoms (Last 2 Weeks)")
    bloating = st.select_slider("Bloating frequency", ["Never", "Rarely", "Sometimes", "Often", "Daily"])
    bowel_regularity = st.select_slider("Bowel movement regularity", ["Very Irregular", "Irregular", "Somewhat Regular", "Regular", "Very Regular"])
    abdominal_pain = st.select_slider("Abdominal pain/discomfort frequency", ["Never", "Rarely", "Sometimes", "Often", "Daily"])
    stool_consistency = st.selectbox("Typical stool consistency", ["Hard/Constipated", "Normal", "Loose/Diarrhea", "Varies a lot"])

    st.header("3. Perceived Stress Scale (PSS-10)")
    st.caption("In the last month, how often have you...")
    pss_answers = []
    for i, q in enumerate(PSS10_QUESTIONS):
        ans = st.select_slider(f"{i+1}. {q}", options=PSS10_OPTIONS, key=f"pss_{i}")
        pss_answers.append(PSS10_OPTIONS.index(ans))

    st.header("4. Stroop Test (Behavioral Stress Measurement)")
    st.write(f"Click the button matching the **INK COLOR** of the word. Complete {TOTAL_STROOP_ROUNDS} rounds.")

    if st.session_state.stroop_round < TOTAL_STROOP_ROUNDS:
        word, ink_name, ink_hex = st.session_state.current_stroop
        st.markdown(f"<h1 style='text-align: center; color: {ink_hex};'>{word}</h1>", unsafe_allow_html=True)

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

    st.header("5. Submit Checkup")
    if st.button("Calculate My Health Baseline"):
        if not st.session_state.stroop_done:
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
                "user_id": user_id, "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "age": age, "gender": gender, "bmi": bmi,
                "bloating": bloating, "abdominal_pain": abdominal_pain,
                "bowel_regularity": bowel_regularity, "stool_consistency": stool_consistency,
                "pss10_score": pss_score, "pss10_result": pss_result,
                "stroop_avg_reaction_time": round(avg_rt, 2), "stroop_accuracy_pct": accuracy,
                "stroop_result": stroop_result,
                "gut_health_score": gut_health_score, "gut_health_category": gut_health_category,
            }
            save_baseline(user_id, record)
            st.balloons()

            color = "#2ECC71" if gut_health_score >= 75 else ("#F39C12" if gut_health_score >= 50 else "#E74C3C")
            bg_color = "#EAFBF1" if gut_health_score >= 75 else ("#FEF6E7" if gut_health_score >= 50 else "#FDEDEC")
            emoji = "🟢" if gut_health_score >= 75 else ("🟡" if gut_health_score >= 50 else "🔴")

            st.markdown(f"""
                <div style="background-color: {bg_color}; border: 2px solid {color}; border-radius: 16px; padding: 30px; text-align: center; margin: 20px 0;">
                    <p style="font-size: 20px; color: #555;">{emoji} YOUR GUT HEALTH RESULT</p>
                    <p style="font-size: 64px; font-weight: 800; color: {color};">{gut_health_score}<span style="font-size: 28px; color: #888;"> / 100</span></p>
                    <p style="font-size: 28px; font-weight: 700; color: {color};">{gut_health_category}</p>
                </div>
            """, unsafe_allow_html=True)

            st.info("💾 Baseline saved! Now go to **Daily Log** in the sidebar to start tracking day by day.")


# ============================================================
# PAGE 2: DAILY LOG
# ============================================================
elif page == "📝 Daily Log (Phase 2)":
    st.title("📝 Daily Lifestyle & Symptom Log")
    st.write("Log today's habits in under a minute. Come back daily to build your personal trend history.")

    st.write(f"Logged in as: **{st.session_state.display_name}**")
    daily_user_id = st.session_state.phone
    log_date = st.date_input("Date", value=date.today())

    st.subheader("Sleep")
    sleep_hours = st.slider("Hours of sleep last night", 0.0, 12.0, 7.0, 0.5)
    sleep_quality = st.select_slider("Sleep quality", ["Poor", "Fair", "Good", "Excellent"])

    st.subheader("Hydration & Diet")
    water_glasses = st.slider("Glasses of water today", 0, 15, 6)
    fiber_servings = st.slider("Servings of fruits/vegetables/whole grains today", 0, 6, 2)
    fried_spicy = st.select_slider("Fried/spicy food today", ["None", "Light", "Moderate", "Heavy"])
    alcohol = st.radio("Alcohol today?", ["No", "Yes"], horizontal=True)

    st.subheader("Activity & Stress")
    exercise_minutes = st.slider("Minutes of physical activity today", 0, 120, 20)
    stress_today = st.slider("Stress level today (1 = very calm, 5 = very stressed)", 1, 5, 3)

    st.subheader("Symptoms Today")
    bloating_today = st.select_slider("Bloating today", ["None", "Mild", "Moderate", "Severe"])
    bowel_movement = st.radio("Had a bowel movement today?", ["Yes", "No"], horizontal=True)

    if st.button("Save Today's Log"):
        if True:
            daily_score = calculate_daily_score(
                sleep_hours, sleep_quality, water_glasses, fiber_servings,
                fried_spicy, alcohol, exercise_minutes, stress_today, bloating_today
            )

            log_entry = {
                "date": log_date.strftime("%Y-%m-%d"),
                "sleep_hours": sleep_hours, "sleep_quality": sleep_quality,
                "water_glasses": water_glasses, "fiber_servings": fiber_servings,
                "fried_spicy": fried_spicy, "alcohol": alcohol,
                "exercise_minutes": exercise_minutes, "stress_today": stress_today,
                "bloating_today": bloating_today, "bowel_movement": bowel_movement,
                "daily_score": daily_score,
            }
            save_daily_log(daily_user_id, log_entry)
            st.balloons()

            color = "#2ECC71" if daily_score >= 75 else ("#F39C12" if daily_score >= 50 else "#E74C3C")
            st.markdown(f"""
                <div style="background-color: #F8F9FA; border: 2px solid {color}; border-radius: 16px; padding: 25px; text-align: center; margin: 15px 0;">
                    <p style="font-size: 18px; color: #555;">TODAY'S SCORE</p>
                    <p style="font-size: 48px; font-weight: 800; color: {color};">{daily_score}<span style="font-size: 22px; color: #888;"> / 100</span></p>
                </div>
            """, unsafe_allow_html=True)
            st.success("Saved! Check 'My Trends' to see your progress over time.")


# ============================================================
# PAGE 3: MY TRENDS
# ============================================================
elif page == "📈 My Trends (Phase 2)":
    st.title("📈 My Health Trends")

    st.write(f"Showing trends for: **{st.session_state.display_name}**")
    trend_user_id = st.session_state.phone
    logs = get_user_logs(trend_user_id)

    if not logs:
        st.warning("No daily logs found yet. Go to 'Daily Log' to add your first entry!")
    else:
            df = pd.DataFrame(logs)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")

            st.subheader(f"Showing {len(df)} logged day(s)")

            st.markdown("### Daily Gut Health Score Over Time")
            st.line_chart(df.set_index("date")["daily_score"])

            if len(df) >= 3:
                df["rolling_avg"] = df["daily_score"].rolling(window=3, min_periods=1).mean()
                st.markdown("### 3-Day Rolling Average (smooths daily ups/downs)")
                st.line_chart(df.set_index("date")["rolling_avg"])

            latest = df.iloc[-1]
            color = "#2ECC71" if latest["daily_score"] >= 75 else ("#F39C12" if latest["daily_score"] >= 50 else "#E74C3C")
            st.markdown(f"""
                <div style="background-color: #F8F9FA; border: 2px solid {color}; border-radius: 16px; padding: 20px; text-align: center; margin: 15px 0;">
                    <p style="font-size: 16px; color: #555;">MOST RECENT SCORE ({latest['date'].strftime('%Y-%m-%d')})</p>
                    <p style="font-size: 40px; font-weight: 800; color: {color};">{latest['daily_score']} / 100</p>
                </div>
            """, unsafe_allow_html=True)

            with st.expander("See full log history (table)"):
                st.dataframe(df.drop(columns=["rolling_avg"], errors="ignore"))