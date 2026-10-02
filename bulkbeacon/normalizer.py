"""Convert raw SerpApi responses into Supplier objects.

NOTE: field names follow SerpApi's documented response formats. Confirm them
against your first real fixture in fixtures/cache/ and adjust if needed.
"""
from urllib.parse import urlparse

from .schemas import Supplier


def maps_to_suppliers(data):
    out = []
    for r in data.get("local_results", []) or []:
        gps = r.get("gps_coordinates") or {}
        out.append(Supplier(
            name=r.get("title", ""),
            source="maps",
            address=r.get("address", ""),
            lat=gps.get("latitude"),
            lng=gps.get("longitude"),
            phone=r.get("phone", "") or "",
            website=r.get("website", "") or "",
            rating=r.get("rating"),
            review_count=int(r.get("reviews") or 0),
            open_state=r.get("open_state", "") or "",
            category=r.get("type", "") or "",
            place_id=r.get("place_id", "") or "",
            link=r.get("website", "") or "",
        ))
    return out


def marketplace_to_suppliers(data, domain="indiamart.com"):
    out = []
    for r in data.get("organic_results", []) or []:
        link = r.get("link", "")
        if domain and domain not in urlparse(link).netloc:
            continue
        out.append(Supplier(name=r.get("title", ""), source="marketplace",
                            link=link, address=r.get("snippet", "")))
    return out


def shopping_to_suppliers(data):
    out = []
    for r in data.get("shopping_results", []) or []:
        out.append(Supplier(
            name=r.get("source", "") or r.get("title", ""),
            source="shopping",
            rating=r.get("rating"),
            review_count=int(r.get("reviews") or 0),
            unit_price=r.get("extracted_price"),
            link=r.get("product_link", "") or r.get("link", ""),
            category=r.get("title", ""),
        ))
    return out


def dedupe(suppliers):
    """Drop duplicates by phone, else by lowercase name + address."""
    seen, out = set(), []
    for s in suppliers:
        key = s.phone.replace(" ", "") if s.phone else f"{s.name.lower()}|{s.address.lower()}"
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out
