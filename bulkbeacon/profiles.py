"""Load category profiles from /profiles/*.json or generate dynamic ones."""
import json
from pathlib import Path
from .schemas import ProductProfile

PROFILE_DIR = Path(__file__).resolve().parent.parent / "profiles"

def load_profiles(only=None):
    out = {}
    for f in sorted(PROFILE_DIR.glob("*.json")):
        p = json.loads(f.read_text(encoding="utf-8"))
        if only is None or p["id"] in only:
            out[p["id"]] = p
    return out

def get_profile(product_name: str) -> ProductProfile:
    normalized = product_name.lower().replace(" ", "_")
    profiles = load_profiles()
    
    # Try exact match first
    for pid, p in profiles.items():
        if pid == normalized or p["name"].lower() == product_name.lower():
            return ProductProfile(**p)
    
    # Generate dynamic profile fallback
    return ProductProfile(
        id=normalized,
        name=product_name,
        category="other",
        validated=False,
        maps_queries=[
            f"{product_name} wholesale supplier {{city}}",
            f"{product_name} distributor {{city}}",
            f"{product_name} manufacturer {{city}}"
        ],
        marketplace_queries=[f"{product_name} dealer {{city}}"],
        shopping_query=f"{product_name} bulk price",
        logistics_query="truck transport service {city}",
        units=["unit", "piece", "kg", "meter", "litre"],
        rfq_fields=[],
        is_dynamic=True
    )
