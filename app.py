import streamlit as st
import pandas as pd
import requests

# Define API key
API_KEY = st.secrets["USDA_API_KEY"]

# Nutrient mapping
NUTRIENT_IDS = {
    1008: "Calories",
    1003: "Protein (g)",
    1004: "Total Fat (g)",
    1005: "Carbohydrates (g)",
    1093: "Sodium (mg)",
    1092: "Potassium (mg)",
    1091: "Phosphorus (mg)",
    1051: "Water (g)",
    2000: "Sugars (g)"  # added sugar if available
}

# CKD thresholds
CKD_LIMITS = {
    "Stage 3": {"Sodium (mg)": 2000, "Potassium (mg)": 3000, "Phosphorus (mg)": 1000},
    "Stage 4": {"Sodium (mg)": 1500, "Potassium (mg)": 2500, "Phosphorus (mg)": 800},
    "Stage 5": {"Sodium (mg)": 1500, "Potassium (mg)": 2000, "Phosphorus (mg)": 700}
}

# Session state for meal tracking
if "meal_log" not in st.session_state:
    st.session_state.meal_log = []

# Search USDA
def search_foods(query, max_results=1):
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {"api_key": API_KEY, "query": query, "pageSize": max_results}
    res = requests.get(url, params=params)
    return res.json().get("foods", []) if res.status_code == 200 else []

# Get nutrients
def extract_nutrients(fdc_id):
    url = f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"
    params = {"api_key": API_KEY}
    res = requests.get(url, params=params)
    if res.status_code != 200:
        return {}
    data = res.json()
    nutrients = data.get("foodNutrients", [])
    result = {}
    for n in nutrients:
        nid = n.get("nutrient", {}).get("id")
        if nid in NUTRIENT_IDS:
            result[NUTRIENT_IDS[nid]] = n.get("amount")
    return result

# Analyze safety
def assess_safety(nutrients, ckd_stage):
    diabetes_safe = "✅" if nutrients.get("Carbohydrates (g)", 0) < 30 and nutrients.get("Sugars (g)", 0) < 10 else "❌"
    ckd_safe = {}
    if ckd_stage in CKD_LIMITS:
        for key, max_val in CKD_LIMITS[ckd_stage].items():
            val = nutrients.get(key, 0)
            ckd_safe[key] = "✅" if val <= max_val else "❌"
    return diabetes_safe, ckd_safe

# Display results
def display_results(food_name, nutrients, ckd_stage):
    st.subheader(food_name)
    df = pd.DataFrame(nutrients.items(), columns=["Nutrient", "Amount (per 100g)"])
    st.dataframe(df)

    diabetes_safe, ckd_safety = assess_safety(nutrients, ckd_stage)

    st.markdown(f"**Diabetes Safe:** {diabetes_safe}")
    st.markdown(f"**CKD Stage {ckd_stage} Safety:**")
    for k, v in ckd_safety.items():
        st.markdown(f"- {k}: {v}")

    # Log meal
    st.session_state.meal_log.append({
        "Food": food_name,
        **nutrients,
        "Diabetes Safe": diabetes_safe,
        "CKD Safety": ckd_safety
    })

# Meal summary
def summarize_meal():
    if not st.session_state.meal_log:
        st.info("No foods added yet.")
        return

    st.subheader("🍽️ Meal Summary")
    df = pd.DataFrame(st.session_state.meal_log)
    df_summary = df.drop(columns=["Food", "Diabetes Safe", "CKD Safety"]).sum(numeric_only=True)
    st.dataframe(df_summary.to_frame(name="Total Nutrients"))

    # Safety summary
    total_carbs = df_summary.get("Carbohydrates (g)", 0)
    total_sugar = df_summary.get("Sugars (g)", 0)
    st.markdown(f"**Total Carbohydrates:** {total_carbs}g")
    st.markdown(f"**Total Sugars:** {total_sugar}g")
    st.markdown(f"**Meal is {'✅ Safe' if total_carbs < 60 and total_sugar < 20 else '❌ Not Safe'} for Diabetes**")

# Streamlit UI
st.title("🥗 Diet Advisor for Diabetes & CKD")
st.markdown("Check nutrient content and dietary safety of your meals.")

query = st.text_input("Enter food name")
ckd_stage = st.selectbox("Select CKD Stage", options=["Stage 3", "Stage 4", "Stage 5"])

if st.button("Analyze"):
    matches = search_foods(query)
    if matches:
        nutrients = extract_nutrients(matches[0]["fdcId"])
        if nutrients:
            display_results(matches[0]["description"], nutrients, ckd_stage)
        else:
            st.error("Failed to extract nutrient info.")
    else:
        st.warning("No match found.")

if st.button("Show Meal Summary"):
    summarize_meal()

if st.button("Clear Meal Log"):
    st.session_state.meal_log = []
    st.success("Meal log cleared.")
