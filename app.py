import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Load USDA API key from secrets
API_KEY = st.secrets["USDA_API_KEY"]

# Nutrients to extract
NUTRIENT_IDS = {
    1008: "Calories",
    1003: "Protein (g)",
    1004: "Total Fat (g)",
    1005: "Carbohydrates (g)",
    1093: "Sodium (mg)",
    1092: "Potassium (mg)",
    1091: "Phosphorus (mg)",
    1051: "Water (g)"
}

# CKD nutrient limits
CKD_LIMITS = {
    "Stage 3": {"Sodium (mg)": 2000, "Potassium (mg)": 3000, "Phosphorus (mg)": 1000},
    "Stage 4": {"Sodium (mg)": 1500, "Potassium (mg)": 2500, "Phosphorus (mg)": 800},
    "Stage 5": {"Sodium (mg)": 1500, "Potassium (mg)": 2000, "Phosphorus (mg)": 700}
}

# Initialize meal log
if "meal_log" not in st.session_state:
    st.session_state.meal_log = []

# USDA Search API
def search_foods(query, max_results=1):
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {"api_key": API_KEY, "query": query, "pageSize": max_results}
    response = requests.get(url, params=params)
    return response.json().get("foods", []) if response.status_code == 200 else []

# Extract nutrient data
def extract_nutrients(fdc_id):
    url = f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"
    params = {"api_key": API_KEY}
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return {}

    data = response.json()
    nutrients = data.get("foodNutrients", [])
    portion = data.get("servingSize")
    unit = data.get("servingSizeUnit")
    result = {"Portion Size": f"{portion} {unit}" if portion and unit else "100 g (default)"}

    for n in nutrients:
        nutrient = n.get("nutrient", {})
        if nutrient.get("id") in NUTRIENT_IDS:
            result[NUTRIENT_IDS[nutrient["id"]]] = n.get("amount")
    return result

# Get food info by name
def get_food_info(query):
    matches = search_foods(query)
    if not matches:
        return [{"Food": query, "Error": "❌ Not found"}]
    results = []
    for match in matches:
        data = extract_nutrients(match["fdcId"])
        if data:
            row = {"Food": match["description"]}
            row.update(data)
            results.append(row)
    return results

# Summarize nutrient totals
def summarize_nutrients(df):
    totals = {}
    for nutrient in ["Sodium (mg)", "Potassium (mg)", "Phosphorus (mg)", "Carbohydrates (g)"]:
        if nutrient in df.columns:
            totals[nutrient] = df[nutrient].sum(skipna=True)
        else:
            totals[nutrient] = 0
    return totals

# ---------------- UI ----------------

st.set_page_config(page_title="CKD + Diabetes Food Tracker", layout="wide")
st.title("🍽️ CKD + Diabetes Nutrient Tracker")
st.caption("Get Potassium and Phosphorus content per food item and total per meal.")

# Stage & Diabetes
col1, col2 = st.columns(2)
with col1:
    stage = st.selectbox("Select CKD Stage", ["Stage 3", "Stage 4", "Stage 5"])
with col2:
    diabetic = st.checkbox("Diabetic?", value=True)

# Input
food_input = st.text_input("Enter food items (comma-separated)", "banana, milk, rice")

if st.button("Analyze"):
    items = [f.strip() for f in food_input.split(",") if f.strip()]
    all_data = []
    for item in items:
        all_data.extend(get_food_info(item))

    df = pd.DataFrame(all_data)

    if df.empty:
        st.error("❌ No nutrient data found.")
    else:
        st.session_state.meal_log.append({
            "timestamp": datetime.now(),
            "foods": food_input,
            "data": df
        })

        totals = summarize_nutrients(df)
        limits = CKD_LIMITS[stage]

        st.subheader("📊 Nutrient Load (Current Meal)")
        for nutrient in ["Sodium (mg)", "Potassium (mg)", "Phosphorus (mg)"]:
            total = totals[nutrient]
            max_val = limits[nutrient]
            percent = (total / max_val) * 100 if max_val else 0
            st.markdown(f"🔹 **{nutrient}: {total:.0f} mg / {max_val} mg** ({percent:.0f}%)")

        if diabetic:
            st.markdown(f"🍞 **Carbohydrates:** {totals['Carbohydrates (g)']:.0f} g (recommended per meal: 45–60 g)")

        st.divider()
        st.subheader("📋 Nutrient Details Per Food")
        st.dataframe(df)

        st.download_button("📥 Download CSV", df.to_csv(index=False), file_name="meal_nutrients.csv")

# Sidebar Meal Log
if st.session_state.meal_log:
    st.sidebar.subheader("📅 Session Meal Log")
    for meal in st.session_state.meal_log[-10:][::-1]:
        st.sidebar.markdown(f"🕒 {meal['timestamp'].strftime('%H:%M')} – {meal['foods']}")

    full_df = pd.concat([m["data"] for m in st.session_state.meal_log], ignore_index=True)
    full_summary = summarize_nutrients(full_df)

    st.sidebar.subheader("🧮 Daily Totals")
    for nutrient in ["Sodium (mg)", "Potassium (mg)", "Phosphorus (mg)"]:
        st.sidebar.markdown(f"🔹 **{nutrient}:** {full_summary[nutrient]:.0f} mg")

    if st.sidebar.button("📥 Download Full Day Log"):
        st.sidebar.download_button("Download CSV", full_df.to_csv(index=False), "full_day_log.csv")

    if st.sidebar.button("🗑️ Clear Log"):
        st.session_state.meal_log = []
        st.sidebar.success("Log cleared.")
