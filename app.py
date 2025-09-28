import streamlit as st
import pandas as pd
import requests
from PIL import Image
from datetime import datetime

# Load USDA API key from secrets
API_KEY = st.secrets["USDA_API_KEY"]

# Nutrient ID mapping from USDA database
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

# CKD stage-specific dietary limits
CKD_LIMITS = {
    "Stage 3": {"Sodium (mg)": 2000, "Potassium (mg)": 3000, "Phosphorus (mg)": 1000},
    "Stage 4": {"Sodium (mg)": 1500, "Potassium (mg)": 2500, "Phosphorus (mg)": 800},
    "Stage 5": {"Sodium (mg)": 1500, "Potassium (mg)": 2000, "Phosphorus (mg)": 700}
}

# Session state initialization
if "meal_log" not in st.session_state:
    st.session_state.meal_log = []

# Search food using USDA API
def search_foods(query, max_results=1):
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {"api_key": API_KEY, "query": query, "pageSize": max_results}
    res = requests.get(url, params=params)
    return res.json().get("foods", []) if res.status_code == 200 else []

# Extract nutrient info from a specific FDC food item
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

# Combine search and nutrient extraction
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

# Streamlit UI
st.title("🥗 DietFriend for Diabetes & CKD")
st.markdown("Analyze your food choices based on CKD stage and nutrient limits.")

query = st.text_input("Enter a food name:")
stage = st.selectbox("Select CKD Stage:", list(CKD_LIMITS.keys()))

if st.button("Analyze"):
    with st.spinner("🔍 Fetching USDA data..."):
        results = get_food_info(query)
        for res in results:
            st.subheader(res.get("Food", "Unknown Item"))
            if "Error" in res:
                st.error(res["Error"])
                continue

            limits = CKD_LIMITS[stage]
            for k, v in res.items():
                if k in ["Food", "Error"]:
                    continue
                if k in limits:
                    if v is not None and v > limits[k]:
                        st.markdown(f"**❌ {k}: {v} (Limit: {limits[k]})**")
                    else:
                        st.markdown(f"✅ {k}: {v}")
                else:
                    st.markdown(f"{k}: {v}")

            # Save to meal log
            res["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.meal_log.append(res)

if st.button("Show Meal Log"):
    if st.session_state.meal_log:
        df = pd.DataFrame(st.session_state.meal_log)
        st.dataframe(df)
    else:
        st.info("No meals logged yet.")


