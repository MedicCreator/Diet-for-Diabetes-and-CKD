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
    1051: "Water (g)"
}

# Search USDA Food Database
def search_foods(query, max_results=1):
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {"api_key": API_KEY, "query": query, "pageSize": max_results}
    res = requests.get(url, params=params)
    return res.json().get("foods", []) if res.status_code == 200 else []

# Extract nutrients per 100g
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

# App UI
st.set_page_config(page_title="Food Nutrient Analyzer", layout="wide")
st.title("🥗 Nutrient Analyzer (Per 100g)")
st.markdown("Enter food names (comma-separated) and get key nutrient content per 100 grams.")

# Input
query = st.text_input("Enter food items", "banana, white bread, milk")

if st.button("Analyze"):
    if query.strip() == "":
        st.warning("Please enter at least one food item.")
    else:
        items = [i.strip() for i in query.split(",") if i.strip()]
        records = []

        for item in items:
            matches = search_foods(item)
            if matches:
                food_desc = matches[0]["description"]
                nutrients = extract_nutrients(matches[0]["fdcId"])
                if nutrients:
                    row = {"Food": food_desc}
                    row.update(nutrients)
                    records.append(row)
                else:
                    st.warning(f"Nutrient data not found for: {item}")
            else:
                st.warning(f"No results for: {item}")

        if records:
            df = pd.DataFrame(records)
            st.subheader("📋 Nutrient Content per 100g")
            st.dataframe(df)

            # Totals
            summary_cols = [col for col in df.columns if col != "Food"]
            total = df[summary_cols].sum(numeric_only=True).to_frame(name="Total per Meal")
            st.subheader("📊 Total Nutrients for All Items")
            st.dataframe(total)

            # Download
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download CSV", data=csv, file_name="nutrient_analysis.csv", mime="text/csv")
        else:
            st.error("No valid nutrient data found.")
