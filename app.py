import streamlit as st
import pandas as pd
import requests
from datetime import datetime

API_KEY = st.secrets["USDA_API_KEY"]

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

if "meal_log" not in st.session_state:
    st.session_state.meal_log = []

# Search food via USDA API
def search_foods(query, max_results=1):
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {"api_key": API_KEY, "query": query, "pageSize": max_results}
    response = requests.get(url, params=params)
    return response.json().get("foods", []) if response.status_code == 200 else []

# Extract nutrients per 100g (standardized)
def extract_nutrients(fdc_id):
    url = f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"
    params = {"api_key": API_KEY}
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return {}

    data = response.json()
    nutrients = data.get("foodNutrients", [])
    result = {"Basis": "Per 100 grams"}
    for n in nutrients:
        nutrient = n.get("nutrient", {})
        if nutrient.get("id") in NUTRIENT_IDS:
            result[NUTRIENT_IDS[nutrient["id"]]] = n.get("amount")
    return result

# Process list of foods
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

# Sum up nutrients
def summarize_nutrients(df):
    totals = {}
    for col in NUTRIENT_IDS.values():
        if col in df.columns:
            totals[col] = df[col].sum(skipna=True)
        else:
            totals[col] = 0
    return totals

# ---------------- UI ----------------

st.set_page_config(page_title="CKD + Diabetes Food Tracker", layout="wide")
st.title("🥗 CKD + Diabetes Nutrient Analyzer")
st.caption("Nutrient values displayed per 100 grams of each food item.")

# Input
food_input = st.text_input("Enter food items (comma-separated)", "banana, rice, boiled egg")

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

        st.subheader("📊 Total Nutrients (All Inputs Combined - 100g Each)")
        for label in NUTRIENT_IDS.values():
            st.markdown(f"🔸 **{label}: {totals[label]:.2f}**")

        st.divider()
        st.subheader("📋 Nutrients Per 100g of Each Food")
        st.dataframe(df)

        st.download_button("📥 Download CSV", df.to_csv(index=False), file_name="food_nutrients_100g.csv")

# Sidebar: Meal log
if st.session_state.meal_log:
    st.sidebar.subheader("🧾 Today's Meal Log")
    for meal in st.session_state.meal_log[-10:][::-1]:
        st.sidebar.markdown(f"🕒 {meal['timestamp'].strftime('%H:%M')} – {meal['foods']}")

    full_df = pd.concat([m["data"] for m in st.session_state.meal_log], ignore_index=True)
    full_totals = summarize_nutrients(full_df)

    st.sidebar.subheader("📈 Combined Nutrients So Far (Per 100g Each)")
    for label in NUTRIENT_IDS.values():
        st.sidebar.markdown(f"✅ **{label}: {full_totals[label]:.2f}**")

    if st.sidebar.button("📥 Download Full Log"):
        st.sidebar.download_button("Download CSV", full_df.to_csv(index=False), "full_day_log.csv")

    if st.sidebar.button("🗑️ Clear Log"):
        st.session_state.meal_log = []
        st.sidebar.success("Meal log cleared.")

