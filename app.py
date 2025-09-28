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
        nutrient_info = n.get("nutrient", {})
        nid = nutrient_info.get("id")
        if nid in NUTRIENT_IDS:
            result[NUTRIENT_IDS[nid]] = n.get("amount")

    return result
