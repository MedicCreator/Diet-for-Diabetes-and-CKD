import streamlit as st
import pandas as pd
import requests
from PIL import Image
from datetime import datetime

# Load USDA API key from Streamlit secrets
API_KEY = st.secrets["USDA_API_KEY"]

# Nutrient IDs to extract from USDA API
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

# CKD nutrient limits by stage
CKD_LIMITS = {
    "Stage 3": {"Sodium (mg)": 2000, "Potassium (mg)": 3000, "Phosphorus (mg)": 1000},
    "Stage 4": {"Sodium (mg)": 1500, "Potassium (mg)": 2500, "Phosphorus (mg)": 800},
    "Stage 5": {"Sodium (mg)": 1500, "Potassium (mg)": 2000, "Phosphorus (mg)": 700}
}

# Initialize meal log in session
if "meal_log" not in st.session_state:
    st.session_state.meal_log = []

# --- Function to search USDA for food items ---
def search_foods(query, max_results=1):
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {"api_key": API_KEY, "query": query, "pageSize": max_results}
    res = requests.get(url, params=params)
    return res.json().get("foods", []) if res.status_code == 200 else []

# --- Function to extract nutrients from USDA by FDC ID ---
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

# --- Function to get nutrient info and label safety ---
def get_food_info(query, stage):
    matches = search_foods(query)
    if not matches:
        return [{"Food": query, "Error": "❌ Not found"}]

    results = []
    limits = CKD_LIMITS[stage]
    for match in matches:
        data = extract_nutrients(match["fdcId"])
        if data:
            entry = {"Food": match["description"]}
            entry.update(data)
            for nutrient in ["Potassium (mg)", "Phosphorus (mg)"]:
                val = entry.get(nutrient)
                if val is not None:
                    if val < 0.6 * limits[nutrient]:
                        entry[f"{nutrient} Safety"] = "🟢 Safe"
                    elif val <= limits[nutrient]:
                        entry[f"{nutrient} Safety"] = "🟡 Caution"
                    else:
                        entry[f"{nutrient} Safety"] = "🔴 High"
            results.append(entry)
    return results

# ====================== Streamlit App Layout ======================

st.set_page_config(page_title="CKD & Diabetes Diet Friend", layout="centered")

st.title("🥦 Diet Friend for Diabetes & CKD")
st.caption("Personalized food analyzer for kidney-conscious eating.")

# CKD Stage selection
stage = st.selectbox("Select CKD Stage", list(CKD_LIMITS.keys()))

# Food input
food_input = st.text_input("Enter a food to analyze:")
if st.button("Analyze Food") and food_input:
    entries = get_food_info(food_input, stage)
    st.session_state.meal_log.extend(entries)

# Meal log display
if st.session_state.meal_log:
    st.subheader("🧾 Meal Log")
    df = pd.DataFrame(st.session_state.meal_log)
    st.dataframe(df.fillna(""), use_container_width=True)

    # Nutrient totals
    st.subheader("📊 Total Nutrient Summary")
    totals = {}
    for nutrient in ["Calories", "Protein (g)", "Total Fat (g)", "Carbohydrates (g)", "Sodium (mg)", "Potassium (mg)", "Phosphorus (mg)"]:
        vals = df[nutrient].dropna()
        totals[nutrient] = vals.sum() if not vals.empty else 0
        st.markdown(f"**{nutrient}:** {totals[nutrient]:.1f}")

    # Nutrient Load and Safety
    limits = CKD_LIMITS[stage]
    st.subheader("🔎 Nutrient Load (Current Meal)")
    for nutrient in ["Sodium (mg)", "Potassium (mg)", "Phosphorus (mg)"]:
        total = totals[nutrient]
        max_val = limits[nutrient]
        percent = (total / max_val) * 100 if max_val else 0
        color = "🟢" if percent < 60 else "🟡" if percent < 100 else "🔴"
        st.markdown(f"{color} **{nutrient}: {total:.0f} mg / {max_val} mg** ({percent:.0f}%)")

    # Clear log
    if st.button("🗑️ Clear Meal Log"):
        st.session_state.meal_log = []

# Footer
st.markdown("---")
st.caption("Built with ❤️ using Streamlit & USDA API")

