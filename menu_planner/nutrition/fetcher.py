"""
nutrition/fetcher.py — Fetch nutritional data from Open Food Facts API.
Falls back to empty dict on any error (no API key required).
"""
import urllib.request
import urllib.parse
import json

OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"


def fetch_nutrition(dish_name: str) -> dict:
    """
    Query Open Food Facts for a dish name.
    Returns dict with keys: calories, protein, carbs, fat, fiber
    or empty strings if not found / on error.
    """
    empty = {"calories": "", "protein": "", "carbs": "", "fat": "", "fiber": ""}
    try:
        params = urllib.parse.urlencode({
            "search_terms": dish_name,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 5,
            "fields": "product_name,nutriments",
        })
        url = f"{OFF_SEARCH_URL}?{params}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "MenuPlanner/1.0 (educational project)"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        products = data.get("products", [])
        if not products:
            return empty

        for prod in products:
            n = prod.get("nutriments", {})
            if not n:
                continue
            kcal = n.get("energy-kcal_100g") or n.get("energy_100g", "")
            prot = n.get("proteins_100g", "")
            carbs = n.get("carbohydrates_100g", "")
            fat = n.get("fat_100g", "")
            fiber = n.get("fiber_100g", "")

            def fmt(val, unit):
                if val == "":
                    return ""
                try:
                    return f"{float(val):.1f} {unit}"
                except (ValueError, TypeError):
                    return str(val)

            return {
                "calories": fmt(kcal, "kcal"),
                "protein":  fmt(prot, "g"),
                "carbs":    fmt(carbs, "g"),
                "fat":      fmt(fat, "g"),
                "fiber":    fmt(fiber, "g"),
            }
        return empty
    except Exception:
        return empty
