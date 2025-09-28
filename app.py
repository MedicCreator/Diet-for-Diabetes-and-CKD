import streamlit as st
import pandas as pd
import requests
from PIL import Image
from datetime import datetime

# ✅ Load your API key securely
API_KEY = st.secrets["USDA_API_KEY"]

# ✅ Nutrient mapping for extraction
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

# ✅ CKD thresholds
CKD_LIMITS = {
    "Stage 3": {"Sodium (mg)": 2000, "Potassium (mg)": 3000, "Phosphorus (mg)": 1000},
    "Stage 4": {"Sodium (mg)": 1500, "Potassium (mg)": 2500, "Phosphorus (mg)": 800},
    "Stage 5": {"Sodium (mg)": 1500, "Potassium (mg)": 2000, "Phosphorus (mg)": 700}
}

# ✅ Init session state
if "meal_log" not in st.session_state:
    st.session_state.meal_log = []

# ✅ API Search
def search_foods(query, max_results=1):
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {"api_key": API_KEY, "query": query, "pageSize": max_results}
    res = requests.get(url, params=params)
    return res.json().get("foods", []) if res.status_code == 200 else []

# ✅ Extract nutrition from USDA
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

# ✅ Check potassium safety
def get_food_info(query, stage):
    matches = search_foods(query)
    if not matches:
        return [{"Food": query, "Error": "❌ Not found"}]
    
    results = []
    k_limit = CKD_LIMITS[stage]["Potassium (mg)"]
    
    for match in matches:
        data = extract_nutrients(match["fdcId"])
        if data:
            potassium = data.get("Potassium (mg)", 0)
            safe = "✅ Safe" if potassium <= k_limit else "❌ High"
            entry = {
                "Food": match["description"],
                "Potassium (mg)": potassium,
                "Potassium Safety": safe
            }
            entry.update(data)
            results.append(entry)
    return results

# ✅ Nutrient summarizer
def summarize_nutrients(df):
    totals = {}
    for nutrient in ["Sodium (mg)", "Potassium (mg)", "Phosphorus (mg)", "Carbohydrates (g)"]:
        totals[nutrient] = df[nutrient].sum() if nutrient in df else 0
    return totals

# ===== UI =====

st.title("🥗 Diet Friend for Diabetes and CKD")
st.markdown("Analyze your meals for **sodium, potassium, phosphorus**, and **carbohydrates**.")

col1, col2 = st.columns(2)
with col1:
    stage = st.selectbox("CKD Stage", ["Stage 3", "Stage 4", "Stage 5"])
with col2:
    diabetic = st.checkbox("I have diabetes")

food_input = st.text_input("Enter food items (comma separated)", placeholder="e.g. banana, grilled chicken, rice")

if st.button("Analyze"):
    items = [f.strip() for f in food_input.split(",") if f.strip()]
    all_data = []
    for item in items:
        all_data.extend(get_food_info(item, stage))  # pass stage

    df = pd.DataFrame(all_data)

    if df.empty:
        st.error("❌ No valid nutrient data found.")
    else:
        st.session_state.meal_log.append({
            "timestamp": datetime.now(),
            "foods": food_input,
            "data": df
        })

        totals = summarize_nutrients(df)
        limits = CKD_LIMITS[stage]

        st.subheader("🔎 Nutrient Load (Current Meal)")
        for nutrient in ["Sodium (mg)", "Potassium (mg)", "Phosphorus (mg)"]:
            total = totals[nutrient]
            max_va_
