import streamlit as st
import pandas as pd
import requests
from PIL import Image
from datetime import datetime

# 🔐 Load your USDA API Key from Streamlit Secrets
API_KEY = st.secrets["USDA_API_KEY"]

# Nutrient IDs to extract from USDA
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

# CKD Stage limits (used for display only)
CKD_LIMITS = {
    "Stage 3": {"Sodium (mg)": 2000, "Potassium (mg)": 3000, "Phosphorus (mg)": 1000},
    "Stage 4": {"Sodium (mg)": 1500, "Potassium (mg)": 2500, "Phosphorus (mg)": 800},
    "Stage 5": {"Sodium (mg)": 1500, "Potassium (mg)": 2000, "Phosphorus (mg)": 700}
}

# 📋 Track meals across app session
if "meal_log" not in st.session_state:
    st.session_state.meal_log = []

# 🔍 Search USDA for a food name
def search_foods(query, max_results=1):
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {"api_key": API_KEY, "query": query, "pageSize": max_results}
    res = requests.get(url, params=params)
    return res.json().get("foods", []) if res.status_code == 200 else []

# 📦 Extract nutrients for a specific food item
def extract_nutrients(fdc_id):
    url = f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"
    params = {"api_key": API_KEY}
    res = requests.get(url, params=params)
    if res.status_code != 200:
        return {}
    data = res.json()
    nutrients = data.get("foodNutrients", [])
    portion = data.get("servingSize")
    unit = data.get("servingSizeUnit")
    result = {"Portion Size": f"{portion} {unit}" if portion and unit else "100 g (default)"}
    for n in nutrients:
        nid = n.get("nutrient", {}).get("id")
        if nid in NUTRIENT_IDS:
            result[NUTRIENT_IDS[nid]] = n.get("amount")
    return result

# 🔄 Process multiple food items
def get_food_info(query):
    matches = search_foods(query)
    if not matches:
        return [{"Food": query, "Error": "❌ Not found"}]
    results = []
    for match in matches:
        data = extract_nutrients(match["fdcId"])
        if data:
            entry = {"Food": match["description"]}
            entry.update(data)
            results.append(entry)
    return results

# ➕ Aggregate nutrient totals
def summarize_nutrients(df):
    summary = {}
    for col in ["Calories", "Protein (g)", "Total Fat (g)", "Carbohydrates (g)", "Sodium (mg)", "Potassium (mg)", "Phosphorus (mg)"]:
        summary[col] = df[col].sum(skipna=True) if col in df.columns else 0
    return summary

# ==================== STREAMLIT UI ====================

st.set_page_config(page_title="CKD + Diabetes Food Tracker", layout="centered")
st.title("🥦 CKD + Diabetes Diet Analyzer")
st.caption("Enter food items to view their nutrient content using USDA database")

# Select stage
stage = st.selectbox("CKD Stage", list(CKD_LIMITS.keys()))
ckd_limits = CKD_LIMITS[stage]

# Input food
food_input = st.text_input("Enter food items (comma-separated)", "banana, milk")

# Button to trigger analysis
if st.button("Analyze"):
    items = [f.strip() for f in food_input.split(",") if f.strip()]
    all_data = []
    for item in items:
        all_data.extend(get_food_info(item))

    df = pd.DataFrame(all_data)
    if df.empty:
        st.error("❌ No nutrient data found.")
    else:
        # Log meal
        st.session_state.meal_log.append({
            "timestamp": datetime.now(),
            "foods": food_input,
            "data": df
        })

        # Totals
        totals = summarize_nutrients(df)

        st.subheader("📊 Nutrient Load for This Meal")
        for nutrient in ["Sodium (mg)", "Potassium (mg)", "Phosphorus (mg)"]:
            total = totals[nutrient]
            limit = ckd_limits[nutrient]
            percent = (total / limit) * 100 if limit else 0
            st.markdown(f"**{nutrient}:** {total:.0f} mg / {limit} mg ({percent:.0f}%)")

        st.subheader("📋 Nutrient Details Per Food")
        st.dataframe(df.fillna(""), use_container_width=True)

        st.download_button("📥 Download This Meal as CSV", df.to_csv(index=False), file_name="ckd_meal.csv")

# Meal log summary
if st.session_state.meal_log:
    st.sidebar.subheader("📅 Meal Log")
    full_df = pd.concat([m["data"] for m in st.session_state.meal_log], ignore_index=True)
    st.sidebar.markdown(f"🧾 {len(st.session_state.meal_log)} meals logged.")
    full_summary = summarize_nutrients(full_df)

    for nutrient in ["Sodium (mg)", "Potassium (mg)", "Phosphorus (mg)"]:
        st.sidebar.markdown(f"🔹 {nutrient}: {full_summary[nutrient]:.0f} mg")

    if st.sidebar.button("🗑️ Clear Log"):
        st.session_state.meal_log = []
        st.sidebar.success("Meal log cleared.")

