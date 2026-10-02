"""Shared data contract. Everyone builds against these shapes."""
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

@dataclass
class Supplier:
    name: str
    source: str                      # "maps" | "marketplace" | "shopping"
    address: str = ""
    lat: Optional[float] = None
    lng: Optional[float] = None
    phone: str = ""
    website: str = ""
    rating: Optional[float] = None
    review_count: int = 0
    open_state: str = ""
    category: str = ""
    unit_price: Optional[float] = None
    link: str = ""
    place_id: str = ""
    distance_km: Optional[float] = None
    trust: dict = field(default_factory=dict)
    rank_breakdown: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

@dataclass
class Request:
    raw_text: str
    item: str = ""
    quantity: Optional[float] = None
    unit: str = "unit"
    city: str = ""
    deadline: str = ""
    urgency: str = "high"
    specs: dict = field(default_factory=dict)
    profile_id: str = ""

@dataclass
class ProductProfile:
    id: str
    name: str
    category: str = "other"
    validated: bool = False
    maps_queries: List[str] = field(default_factory=lambda: ["{product} wholesale supplier {city}", "{product} distributor {city}"])
    marketplace_queries: List[str] = field(default_factory=lambda: ["{product} wholesale {city}"])
    marketplace_domain: str = "indiamart.com"
    shopping_query: str = "{product} bulk"
    logistics_query: str = "truck transport service {city}"
    units: List[str] = field(default_factory=lambda: ["unit", "piece", "kg"])
    urgency_weight: float = 0.5
    rfq_fields: List[str] = field(default_factory=list)
    price_reference: str = "retail_only"
    is_dynamic: bool = False
    
    def __getitem__(self, item):
        return getattr(self, item)
    
    def get(self, item, default=None):
        return getattr(self, item, default)

    def __contains__(self, item):
        return hasattr(self, item)
