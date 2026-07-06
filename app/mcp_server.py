"""Crop Doctor MCP Server — Plant disease database and treatment catalog.

Provides domain-specific tools for the Crop Doctor agent system via stdio transport.
"""

import json
import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("crop-doctor-mcp")

# ---------------------------------------------------------------------------
# Plant Disease Database (simulated knowledge base)
# ---------------------------------------------------------------------------

DISEASE_DB = {
    "early_blight": {
        "name": "Early Blight (Alternaria solani)",
        "affects": ["tomato", "potato", "eggplant", "pepper"],
        "symptoms": ["dark concentric rings on leaves", "yellowing around spots",
                      "lower leaves affected first", "stem lesions", "fruit rot"],
        "conditions": ["warm humid weather", "temperature 24-29°C",
                       "overhead irrigation", "poor air circulation"],
        "contagious": True,
        "urgency": "high",
    },
    "powdery_mildew": {
        "name": "Powdery Mildew (Erysiphe spp.)",
        "affects": ["wheat", "cucumber", "squash", "grape", "mango", "pea"],
        "symptoms": ["white powdery coating on leaves", "leaf curling",
                      "stunted growth", "premature leaf drop"],
        "conditions": ["dry weather with cool nights", "temperature 15-28°C",
                       "high humidity", "shaded areas"],
        "contagious": True,
        "urgency": "medium",
    },
    "bacterial_wilt": {
        "name": "Bacterial Wilt (Ralstonia solanacearum)",
        "affects": ["tomato", "potato", "eggplant", "banana", "ginger"],
        "symptoms": ["sudden wilting without yellowing", "brown discoloration in stem",
                      "bacterial ooze from cut stem", "plants die within days"],
        "conditions": ["waterlogged soil", "temperature 25-35°C",
                       "contaminated tools", "infected transplants"],
        "contagious": True,
        "urgency": "critical",
    },
    "leaf_rust": {
        "name": "Leaf Rust (Puccinia spp.)",
        "affects": ["wheat", "barley", "rice", "corn", "sugarcane"],
        "symptoms": ["orange-brown pustules on leaves", "yellowing leaves",
                      "reduced grain filling", "premature senescence"],
        "conditions": ["cool moist weather", "temperature 15-22°C",
                       "heavy dew", "dense planting"],
        "contagious": True,
        "urgency": "high",
    },
    "root_rot": {
        "name": "Root Rot (Pythium/Phytophthora spp.)",
        "affects": ["soybean", "cotton", "bean", "pea", "chili", "papaya"],
        "symptoms": ["yellowing and wilting", "brown mushy roots",
                      "stunted growth", "plant collapse"],
        "conditions": ["overwatering", "poor drainage", "heavy clay soil",
                       "temperature 20-30°C"],
        "contagious": False,
        "urgency": "high",
    },
    "mosaic_virus": {
        "name": "Mosaic Virus (TMV/CMV)",
        "affects": ["tomato", "tobacco", "cucumber", "pepper", "bean"],
        "symptoms": ["mottled yellow-green leaves", "leaf distortion",
                      "stunted growth", "reduced fruit quality"],
        "conditions": ["aphid transmission", "contaminated seeds",
                       "mechanical transmission via tools"],
        "contagious": True,
        "urgency": "medium",
    },
    "downy_mildew": {
        "name": "Downy Mildew (Peronospora/Pseudoperonospora spp.)",
        "affects": ["grape", "cucumber", "onion", "spinach", "lettuce"],
        "symptoms": ["yellow patches on upper leaf", "gray-purple fuzz underneath",
                      "leaf necrosis", "defoliation"],
        "conditions": ["cool wet weather", "temperature 10-20°C",
                       "rain and fog", "poor ventilation"],
        "contagious": True,
        "urgency": "high",
    },
    "nutrient_deficiency_nitrogen": {
        "name": "Nitrogen Deficiency",
        "affects": ["all crops"],
        "symptoms": ["pale green to yellow leaves", "older leaves affected first",
                      "stunted growth", "thin stems", "reduced yield"],
        "conditions": ["sandy soil", "heavy rainfall leaching",
                       "insufficient fertilization"],
        "contagious": False,
        "urgency": "medium",
    },
}

# ---------------------------------------------------------------------------
# Treatment Catalog
# ---------------------------------------------------------------------------

TREATMENT_DB = {
    "early_blight": {
        "organic": ["Neem oil spray (3ml/L water, every 7 days)",
                     "Copper-based fungicide (Bordeaux mixture)",
                     "Remove and destroy infected leaves",
                     "Mulch around base to prevent soil splash"],
        "chemical": ["Mancozeb 75% WP (2.5g/L, spray every 10 days)",
                      "Chlorothalonil fungicide",
                      "Azoxystrobin (caution: wear protective gear)"],
        "prevention": ["Crop rotation (3 year cycle)",
                       "Use disease-resistant varieties",
                       "Avoid overhead watering",
                       "Ensure proper plant spacing for air flow"],
        "recovery_days": 14,
    },
    "powdery_mildew": {
        "organic": ["Baking soda spray (1 tbsp/gallon water + dish soap)",
                     "Milk spray (40% milk + 60% water)",
                     "Neem oil spray weekly",
                     "Sulfur-based fungicide"],
        "chemical": ["Propiconazole fungicide",
                      "Myclobutanil spray",
                      "Tebuconazole (systemic)"],
        "prevention": ["Improve air circulation",
                       "Avoid excess nitrogen fertilizer",
                       "Plant resistant varieties",
                       "Water at base, not overhead"],
        "recovery_days": 10,
    },
    "bacterial_wilt": {
        "organic": ["Remove and burn infected plants immediately",
                     "Solarize soil for 4-6 weeks",
                     "Apply Trichoderma-based biocontrol",
                     "Add organic matter to improve drainage"],
        "chemical": ["No effective chemical treatment — prevention is key",
                      "Soil fumigation with metam sodium (last resort)"],
        "prevention": ["Use certified disease-free transplants",
                       "Sanitize all tools with bleach solution",
                       "Improve field drainage",
                       "Rotate with non-solanaceous crops for 3+ years"],
        "recovery_days": 0,
    },
    "leaf_rust": {
        "organic": ["Remove infected plant debris",
                     "Apply sulfur dust in early morning",
                     "Use resistant wheat/barley varieties"],
        "chemical": ["Propiconazole 25% EC (1ml/L water)",
                      "Tebuconazole spray at flag leaf stage",
                      "Mancozeb (preventive application)"],
        "prevention": ["Plant rust-resistant varieties",
                       "Early sowing to avoid peak rust season",
                       "Balanced fertilization",
                       "Monitor fields weekly during cool moist periods"],
        "recovery_days": 21,
    },
    "root_rot": {
        "organic": ["Improve drainage immediately",
                     "Apply Trichoderma to soil",
                     "Reduce watering frequency",
                     "Add perlite/sand to heavy soil"],
        "chemical": ["Metalaxyl (Ridomil) soil drench",
                      "Fosetyl-Al fungicide"],
        "prevention": ["Avoid overwatering",
                       "Use raised beds in heavy soil",
                       "Ensure proper field drainage",
                       "Rotate crops annually"],
        "recovery_days": 21,
    },
    "mosaic_virus": {
        "organic": ["Remove and destroy infected plants",
                     "Control aphid vectors with neem oil",
                     "Use reflective mulch to repel aphids"],
        "chemical": ["Imidacloprid for aphid control (vector management)",
                      "No direct chemical cure for virus"],
        "prevention": ["Use virus-free certified seeds",
                       "Control aphid populations early",
                       "Sanitize tools between plants",
                       "Plant border crops as virus barriers"],
        "recovery_days": 0,
    },
    "downy_mildew": {
        "organic": ["Copper hydroxide spray",
                     "Improve air circulation by pruning",
                     "Remove infected leaves promptly"],
        "chemical": ["Metalaxyl + Mancozeb combination",
                      "Dimethomorph fungicide",
                      "Cymoxanil spray"],
        "prevention": ["Avoid overhead irrigation",
                       "Plant resistant varieties",
                       "Ensure proper spacing",
                       "Scout fields during cool wet periods"],
        "recovery_days": 14,
    },
    "nutrient_deficiency_nitrogen": {
        "organic": ["Apply well-composted manure",
                     "Use blood meal or fish emulsion",
                     "Plant nitrogen-fixing cover crops (legumes)",
                     "Apply vermicompost"],
        "chemical": ["Urea (46-0-0) at recommended rate",
                      "Ammonium sulfate side-dressing",
                      "Foliar spray of 2% urea solution"],
        "prevention": ["Soil test before each season",
                       "Maintain organic matter in soil",
                       "Use balanced NPK fertilizers",
                       "Incorporate crop residues"],
        "recovery_days": 7,
    },
}


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def lookup_disease(plant_name: str, symptoms: str) -> str:
    """Search the plant disease database for diseases matching the given plant and symptoms.

    Args:
        plant_name: The name of the affected plant/crop (e.g., 'tomato', 'wheat', 'rice')
        symptoms: Comma-separated list of observed symptoms (e.g., 'yellow leaves, wilting, spots')

    Returns:
        JSON string with matching diseases and their details.
    """
    plant_lower = plant_name.lower()
    symptom_list = [s.strip().lower() for s in symptoms.split(",")]

    matches = []
    for disease_id, info in DISEASE_DB.items():
        # Check if plant is affected
        plant_match = any(plant_lower in crop for crop in info["affects"]) or "all crops" in info["affects"]

        # Check symptom overlap
        symptom_score = 0
        for symptom in symptom_list:
            for db_symptom in info["symptoms"]:
                if symptom in db_symptom.lower() or any(word in db_symptom.lower() for word in symptom.split()):
                    symptom_score += 1
                    break

        if plant_match and symptom_score > 0:
            matches.append({
                "disease_id": disease_id,
                "name": info["name"],
                "match_score": symptom_score,
                "matching_symptoms": info["symptoms"],
                "favorable_conditions": info["conditions"],
                "contagious": info["contagious"],
                "urgency": info["urgency"],
            })

    matches.sort(key=lambda x: x["match_score"], reverse=True)

    if not matches:
        return json.dumps({
            "status": "no_match",
            "message": f"No exact match found for {plant_name} with symptoms: {symptoms}. "
                       "Consider consulting a local agricultural extension office.",
            "suggestion": "Describe symptoms more specifically: leaf color, spots, wilting pattern, growth changes.",
        })

    return json.dumps({"status": "found", "matches": matches[:3]})


@mcp.tool()
def get_treatment_catalog(disease_id: str) -> str:
    """Look up recommended treatments for a specific plant disease.

    Args:
        disease_id: The disease identifier (e.g., 'early_blight', 'powdery_mildew', 'bacterial_wilt')

    Returns:
        JSON string with organic options, chemical options, prevention tips, and recovery timeline.
    """
    treatment = TREATMENT_DB.get(disease_id)
    if not treatment:
        return json.dumps({
            "status": "not_found",
            "message": f"No treatment found for disease_id: {disease_id}",
            "available_diseases": list(TREATMENT_DB.keys()),
        })

    return json.dumps({
        "status": "found",
        "disease_id": disease_id,
        "organic_treatments": treatment["organic"],
        "chemical_treatments": treatment["chemical"],
        "prevention_tips": treatment["prevention"],
        "estimated_recovery_days": treatment["recovery_days"],
    })


@mcp.tool()
def get_weather_risk(region: str, season: str) -> str:
    """Check weather-based disease risk factors for a farming region and season.

    Args:
        region: The farming region or climate zone (e.g., 'tropical', 'subtropical', 'temperate', 'arid')
        season: Current growing season (e.g., 'kharif', 'rabi', 'summer', 'monsoon', 'winter', 'spring')

    Returns:
        JSON string with weather risk assessment and disease alerts.
    """
    risk_profiles = {
        ("tropical", "monsoon"): {
            "risk_level": "HIGH",
            "conditions": "Heavy rainfall, high humidity (>80%), warm temperatures (25-35°C)",
            "high_risk_diseases": ["bacterial_wilt", "root_rot", "downy_mildew", "leaf_rust"],
            "advisory": "Ensure field drainage. Avoid waterlogging. Scout daily for wilting symptoms.",
        },
        ("tropical", "summer"): {
            "risk_level": "MEDIUM",
            "conditions": "Hot and dry, temperature 30-45°C, low humidity",
            "high_risk_diseases": ["powdery_mildew", "mosaic_virus", "nutrient_deficiency_nitrogen"],
            "advisory": "Irrigate regularly. Watch for aphid-borne viruses. Apply mulch to retain moisture.",
        },
        ("subtropical", "kharif"): {
            "risk_level": "HIGH",
            "conditions": "Warm and wet monsoon season, humidity >75%",
            "high_risk_diseases": ["early_blight", "bacterial_wilt", "downy_mildew"],
            "advisory": "Use disease-resistant varieties. Apply preventive copper sprays. Improve drainage.",
        },
        ("subtropical", "rabi"): {
            "risk_level": "MEDIUM",
            "conditions": "Cool and dry, temperature 10-25°C",
            "high_risk_diseases": ["powdery_mildew", "leaf_rust", "downy_mildew"],
            "advisory": "Monitor for rust in wheat fields. Apply sulfur-based fungicides preventively.",
        },
        ("temperate", "spring"): {
            "risk_level": "MEDIUM",
            "conditions": "Cool and moist, temperature 10-20°C, frequent rain",
            "high_risk_diseases": ["downy_mildew", "leaf_rust", "root_rot"],
            "advisory": "Ensure good drainage. Use fungicide seed treatments.",
        },
        ("temperate", "winter"): {
            "risk_level": "LOW",
            "conditions": "Cold and dry, most pathogens dormant",
            "high_risk_diseases": ["nutrient_deficiency_nitrogen"],
            "advisory": "Good time for soil testing and preparation for next season.",
        },
        ("arid", "summer"): {
            "risk_level": "LOW",
            "conditions": "Hot and very dry, low disease pressure",
            "high_risk_diseases": ["powdery_mildew", "nutrient_deficiency_nitrogen"],
            "advisory": "Focus on irrigation management and soil nutrition.",
        },
    }

    region_lower = region.lower().strip()
    season_lower = season.lower().strip()

    result = risk_profiles.get((region_lower, season_lower))
    if not result:
        # Fuzzy match
        for (r, s), profile in risk_profiles.items():
            if region_lower in r or r in region_lower:
                if season_lower in s or s in season_lower:
                    result = profile
                    break

    if not result:
        return json.dumps({
            "risk_level": "UNKNOWN",
            "message": f"No specific risk profile for region='{region}', season='{season}'.",
            "general_advisory": "Monitor crops regularly. Maintain good drainage and air circulation.",
            "available_regions": ["tropical", "subtropical", "temperate", "arid"],
            "available_seasons": ["monsoon", "summer", "kharif", "rabi", "spring", "winter"],
        })

    return json.dumps(result)


@mcp.tool()
def get_seasonal_advice(region: str, crop: str) -> str:
    """Get season-specific farming advice for a crop in a given region.

    Args:
        region: Farming region (e.g., 'tropical', 'subtropical', 'temperate')
        crop: The crop being grown (e.g., 'tomato', 'wheat', 'rice')

    Returns:
        JSON string with seasonal farming advice and best practices.
    """
    advice_db = {
        "tomato": {
            "best_season": "Rabi (Oct-Feb) or Spring",
            "spacing": "60cm x 45cm",
            "watering": "Regular drip irrigation, avoid wetting leaves",
            "common_issues": ["early_blight", "bacterial_wilt", "mosaic_virus"],
            "tips": [
                "Stake or cage plants for better air circulation",
                "Apply mulch to prevent soil splash",
                "Remove suckers below first fruit cluster",
                "Monitor for hornworm and aphids weekly",
            ],
        },
        "wheat": {
            "best_season": "Rabi (Nov-Mar)",
            "spacing": "Row spacing 20-22.5cm",
            "watering": "4-6 irrigations at critical stages",
            "common_issues": ["leaf_rust", "powdery_mildew"],
            "tips": [
                "Sow at optimal time to avoid terminal heat stress",
                "Apply nitrogen in 2-3 split doses",
                "Scout for rust at tillering and flag leaf stages",
                "Use certified disease-free seed",
            ],
        },
        "rice": {
            "best_season": "Kharif (Jun-Nov)",
            "spacing": "20cm x 15cm (transplanting)",
            "watering": "Maintain 5cm standing water during vegetative stage",
            "common_issues": ["leaf_rust", "bacterial_wilt"],
            "tips": [
                "Use SRI method for better yields",
                "Apply zinc sulfate if deficiency signs appear",
                "Drain field 2 weeks before harvest",
                "Rotate with pulses for soil health",
            ],
        },
    }

    crop_lower = crop.lower().strip()
    info = advice_db.get(crop_lower)

    if not info:
        return json.dumps({
            "status": "not_found",
            "message": f"No specific advice for crop '{crop}' in database.",
            "general_tips": [
                "Test soil before planting",
                "Use quality seeds from certified sources",
                "Follow recommended spacing for your variety",
                "Maintain proper irrigation schedule",
                "Scout fields weekly for pests and diseases",
            ],
        })

    return json.dumps({
        "status": "found",
        "crop": crop,
        "region": region,
        **info,
    })


@mcp.tool()
def get_organic_alternatives(chemical_name: str) -> str:
    """Find organic/natural alternatives to a chemical pesticide or fungicide.

    Args:
        chemical_name: Name of the chemical product (e.g., 'mancozeb', 'imidacloprid', 'urea')

    Returns:
        JSON string with organic alternatives and application methods.
    """
    alternatives = {
        "mancozeb": {
            "organic_alternatives": [
                {"name": "Bordeaux mixture", "application": "Spray 1% solution every 10-14 days"},
                {"name": "Neem oil", "application": "3ml/L water, spray weekly"},
                {"name": "Trichoderma", "application": "Soil application at 2.5kg/hectare"},
            ],
            "note": "Organic options may need more frequent application but are safer for soil biology.",
        },
        "imidacloprid": {
            "organic_alternatives": [
                {"name": "Neem oil extract", "application": "5ml/L water, spray on affected parts"},
                {"name": "Pyrethrin (natural)", "application": "Apply at dusk when bees are inactive"},
                {"name": "Sticky yellow traps", "application": "Place 1 trap per 5 sq meters"},
                {"name": "Ladybug release", "application": "Release 1500/1000 sq ft for aphid control"},
            ],
            "note": "Always manage pests early. Small populations are easier to control organically.",
        },
        "urea": {
            "organic_alternatives": [
                {"name": "Vermicompost", "application": "Apply 5 tons/hectare before planting"},
                {"name": "Fish emulsion", "application": "Dilute 1:5 with water, apply biweekly"},
                {"name": "Blood meal", "application": "Side-dress at 1kg per 10 sq meters"},
                {"name": "Green manure crops", "application": "Grow and incorporate legumes before main crop"},
            ],
            "note": "Organic nitrogen sources release slowly, improving long-term soil health.",
        },
    }

    chemical_lower = chemical_name.lower().strip()
    result = alternatives.get(chemical_lower)

    if not result:
        return json.dumps({
            "status": "not_found",
            "message": f"No specific alternatives found for '{chemical_name}'.",
            "general_advice": "Consult your local agricultural extension office for organic alternatives. "
                              "Neem oil, copper-based fungicides, and biocontrol agents are good starting points.",
        })

    return json.dumps({"status": "found", "chemical": chemical_name, **result})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
