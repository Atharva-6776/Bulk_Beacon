"""BulkBeacon scaffold bootstrap.

Run from the folder where the project should be created:
    python bootstrap_scaffold.py
Creates README.md, requirements.txt, .env.example, .gitignore, bulkbeacon/, profiles/,
scripts/, tests/ and fixtures/cache/. Existing files are NOT overwritten (they are skipped
and reported), and no keys are written anywhere.
"""
import pathlib
import sys

FILES = {}
FILES['.env.example'] = r'''# Copy to .env and fill in. Never commit .env
SERPAPI_KEY=your_serpapi_key_here
# Max real SerpApi calls allowed in one run of a script (credit safety)
BULKBEACON_MAX_CALLS=40
# Set to 1 to run only from saved fixtures (no key, no network)
BULKBEACON_DEMO=0
'''
FILES['.gitignore'] = r'''.env
__pycache__/
*.pyc
.credits.json
.venv/
'''
FILES['README.md'] = r'''# BulkBeacon

Need it in bulk, today? Find suppliers, send quote requests, compare quotes.
Built for the SerpApi India Hackathon 2026 (deadline 10 Oct 2026, 23:59 IST).

> Status: Day 1 scaffold. Implemented: SerpApi client (cache, call cap, demo mode),
> shared schemas, normalizer, category profiles, Day 1 data test. Not yet built:
> parser, trust scorer, ranker, API, frontend, RFQ, quote comparison (see SRS).

## Setup
```
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env, then add your SERPAPI_KEY
python -m unittest discover -s tests -v
```

## Day 1: test which categories have good data in your city
```
python scripts/day1_test.py --city Pune
```
- Costs about 4 SerpApi credits per profile (6 profiles = ~24). Free plan = 250/month.
- Every response is saved to `fixtures/cache/`, so re-running is free. **Commit these
  fixtures** so teammates and demo mode can reuse them (they contain no API key).
- Read `fixtures/day1_report.md`. The 5-point score is only a rough heuristic;
  check that the supplier names are actually relevant to the category.
- Keep the 3 best categories, then set `"validated": true` in their profile files.

## Rules for the team
1. Never commit `.env` or any key.
2. Never call `requests` for SerpApi directly; always use `SerpApiClient` (cache + cap).
3. Build against `bulkbeacon/schemas.py`; change it only after telling everyone.
4. Work on branches; no direct pushes to `main`.
5. `BULKBEACON_DEMO=1` runs from fixtures only (no key, no network).

## Layout
```
bulkbeacon/serpapi_client.py   cached client, call cap, demo mode
bulkbeacon/schemas.py          Supplier / Request contract
bulkbeacon/normalizer.py       Maps / Search / Shopping -> Supplier, dedupe
bulkbeacon/profiles.py         loads profiles/*.json
profiles/                      6 candidate category profiles (unvalidated)
scripts/day1_test.py           data-quality test + report
tests/                         offline unit tests
```

## Limitations (also shown in the app)
Search data cannot give real wholesale prices, verify stock or quality, or prove a
supplier is genuine. Retail prices are benchmarks only; trust scores are risk signals.
'''
FILES['bulkbeacon/__init__.py'] = r''''''
FILES['bulkbeacon/normalizer.py'] = r'''"""Convert raw SerpApi responses into Supplier objects.

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
'''
FILES['bulkbeacon/profiles.py'] = r'''"""Load category profiles from /profiles/*.json."""
import json
from pathlib import Path

PROFILE_DIR = Path(__file__).resolve().parent.parent / "profiles"


def load_profiles(only=None):
    out = {}
    for f in sorted(PROFILE_DIR.glob("*.json")):
        p = json.loads(f.read_text(encoding="utf-8"))
        if only is None or p["id"] in only:
            out[p["id"]] = p
    return out
'''
FILES['bulkbeacon/schemas.py'] = r'''"""Shared data contract. Everyone builds against these shapes."""
from dataclasses import dataclass, field, asdict
from typing import Optional


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
    open_state: str = ""             # raw Maps text, e.g. "Open ⋅ Closes 8 pm"
    category: str = ""               # Maps business type, e.g. "Wholesaler"
    unit_price: Optional[float] = None
    link: str = ""
    place_id: str = ""
    distance_km: Optional[float] = None
    trust: dict = field(default_factory=dict)           # filled by trust scorer
    rank_breakdown: dict = field(default_factory=dict)  # filled by ranker

    def to_dict(self):
        return asdict(self)


@dataclass
class Request:
    raw_text: str
    item: str = ""
    quantity: Optional[float] = None
    unit: str = "kg"
    city: str = ""
    deadline: str = ""
    urgency: str = "high"
    specs: dict = field(default_factory=dict)
    profile_id: str = ""
'''
FILES['bulkbeacon/serpapi_client.py'] = r'''"""SerpApi client with disk cache, credit counter and demo mode.

Every real network call costs one SerpApi credit (free plan: 250/month),
so identical queries are served from fixtures/cache and a hard call cap
protects you from burning credits by accident.
"""
import hashlib
import json
import os
import time
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # dotenv is optional
    pass

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "fixtures" / "cache"
CREDITS_FILE = ROOT / ".credits.json"
ENDPOINT = "https://serpapi.com/search.json"


class DemoModeMiss(Exception):
    """Demo mode is on and the query has no saved fixture."""


class CallCapReached(Exception):
    """The per-run cap on real SerpApi calls was reached."""


class SerpApiClient:
    def __init__(self, api_key=None, demo=None, max_calls=None, cache_dir=CACHE_DIR):
        self.api_key = api_key or os.getenv("SERPAPI_KEY", "")
        self.demo = demo if demo is not None else os.getenv("BULKBEACON_DEMO", "0") == "1"
        self.max_calls = max_calls if max_calls is not None else int(os.getenv("BULKBEACON_MAX_CALLS", "40"))
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.network_calls = 0   # real calls made by this instance
        self.cache_hits = 0

    @staticmethod
    def _key(params):
        clean = {k: v for k, v in params.items() if k != "api_key"}
        return hashlib.sha256(json.dumps(clean, sort_keys=True).encode()).hexdigest()[:16]

    def search(self, **params):
        """Run a SerpApi search. Example: search(engine="google_maps", q="tomato wholesale Pune")"""
        params.setdefault("gl", "in")
        params.setdefault("hl", "en")
        path = self.cache_dir / f"{params.get('engine', 'google')}_{self._key(params)}.json"
        if path.exists():
            self.cache_hits += 1
            return json.loads(path.read_text(encoding="utf-8"))
        if self.demo:
            raise DemoModeMiss(f"No fixture for {params}")
        if not self.api_key:
            raise RuntimeError("SERPAPI_KEY is not set (see .env.example)")
        if self.network_calls >= self.max_calls:
            raise CallCapReached(f"Reached the cap of {self.max_calls} real calls")
        resp = requests.get(ENDPOINT, params={**params, "api_key": self.api_key}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        self.network_calls += 1
        self._bump_credits()
        path.write_text(json.dumps({"_params": dict(params), **data},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
        return data

    @staticmethod
    def _bump_credits():
        used = json.loads(CREDITS_FILE.read_text()) if CREDITS_FILE.exists() else {}
        month = time.strftime("%Y-%m")
        used[month] = used.get(month, 0) + 1
        CREDITS_FILE.write_text(json.dumps(used))

    @staticmethod
    def credits_used_this_month():
        """Calls made from THIS machine only; check your SerpApi dashboard for the real total."""
        if not CREDITS_FILE.exists():
            return 0
        return json.loads(CREDITS_FILE.read_text()).get(time.strftime("%Y-%m"), 0)
'''
FILES['fixtures/cache/.gitkeep'] = r''''''
FILES['profiles/cement.json'] = r'''{
  "id": "cement",
  "name": "Cement",
  "validated": false,
  "maps_queries": [
    "cement dealer {city}",
    "cement wholesale {city}",
    "building material supplier {city}"
  ],
  "marketplace_queries": [
    "cement dealer {city}"
  ],
  "marketplace_domain": "indiamart.com",
  "shopping_query": "cement 50 kg bag",
  "logistics_query": "truck transport service {city}",
  "units": [
    "bag",
    "ton"
  ],
  "urgency_weight": 0.5,
  "rfq_fields": [
    "brand",
    "grade (OPC/PPC)",
    "bag size"
  ],
  "price_reference": "retail_only"
}'''
FILES['profiles/corrugated_boxes.json'] = r'''{
  "id": "corrugated_boxes",
  "name": "Corrugated boxes",
  "validated": false,
  "maps_queries": [
    "corrugated box manufacturer {city}",
    "carton box supplier {city}",
    "packaging box wholesaler {city}"
  ],
  "marketplace_queries": [
    "corrugated boxes manufacturer {city}"
  ],
  "marketplace_domain": "indiamart.com",
  "shopping_query": "corrugated carton box",
  "logistics_query": "tempo transport {city}",
  "units": [
    "piece"
  ],
  "urgency_weight": 0.4,
  "rfq_fields": [
    "size (LxWxH)",
    "ply",
    "GSM",
    "print/no print"
  ],
  "price_reference": "retail_only"
}'''
FILES['profiles/packaging_film.json'] = r'''{
  "id": "packaging_film",
  "name": "Packaging film / stretch wrap",
  "validated": false,
  "maps_queries": [
    "packaging material supplier {city}",
    "stretch film dealer {city}",
    "packaging film wholesaler {city}"
  ],
  "marketplace_queries": [
    "packaging film supplier {city}"
  ],
  "marketplace_domain": "indiamart.com",
  "shopping_query": "stretch wrap film roll",
  "logistics_query": "tempo transport {city}",
  "units": [
    "kg",
    "roll",
    "piece"
  ],
  "urgency_weight": 0.4,
  "rfq_fields": [
    "material",
    "width",
    "thickness (micron)",
    "roll weight"
  ],
  "price_reference": "retail_only"
}'''
FILES['profiles/plastic_granules.json'] = r'''{
  "id": "plastic_granules",
  "name": "Plastic granules (raw material)",
  "validated": false,
  "maps_queries": [
    "plastic granules dealer {city}",
    "polymer raw material supplier {city}",
    "HDPE LDPE granules wholesaler {city}"
  ],
  "marketplace_queries": [
    "plastic granules supplier {city}"
  ],
  "marketplace_domain": "indiamart.com",
  "shopping_query": "HDPE granules 25 kg",
  "logistics_query": "truck transport service {city}",
  "units": [
    "kg",
    "ton",
    "bag"
  ],
  "urgency_weight": 0.4,
  "rfq_fields": [
    "polymer type",
    "grade",
    "virgin/recycled",
    "MFI"
  ],
  "price_reference": "retail_only"
}'''
FILES['profiles/tmt_steel.json'] = r'''{
  "id": "tmt_steel",
  "name": "TMT bars / steel",
  "validated": false,
  "maps_queries": [
    "TMT bar dealer {city}",
    "steel stockist {city}",
    "iron and steel wholesaler {city}"
  ],
  "marketplace_queries": [
    "TMT bars supplier {city}"
  ],
  "marketplace_domain": "indiamart.com",
  "shopping_query": "TMT bar 12mm",
  "logistics_query": "truck transport service {city}",
  "units": [
    "kg",
    "ton",
    "piece"
  ],
  "urgency_weight": 0.5,
  "rfq_fields": [
    "grade (e.g. Fe500)",
    "diameter",
    "brand",
    "IS standard"
  ],
  "price_reference": "published"
}'''
FILES['profiles/tomatoes.json'] = r'''{
  "id": "tomatoes",
  "name": "Tomatoes (fresh produce)",
  "validated": false,
  "maps_queries": [
    "tomato wholesale {city}",
    "vegetable commission agent {city}",
    "APMC mandi {city}"
  ],
  "marketplace_queries": [
    "tomato wholesale supplier {city}"
  ],
  "marketplace_domain": "indiamart.com",
  "shopping_query": "tomato 1 kg",
  "logistics_query": "mini truck rental {city}",
  "units": [
    "kg",
    "ton",
    "crate"
  ],
  "urgency_weight": 0.9,
  "rfq_fields": [
    "variety",
    "grade",
    "freshness",
    "packing (crate/bag)"
  ],
  "price_reference": "mandi"
}'''
FILES['requirements.txt'] = r'''requests>=2.31
python-dotenv>=1.0
'''
FILES['scripts/day1_test.py'] = r'''"""Day 1 data-quality test.

Runs real SerpApi queries for each candidate category in your city, saves every
response as a fixture, and prints a quality report so the team can pick the 3
categories with the best data.

Usage:
  python scripts/day1_test.py --city Pune
  python scripts/day1_test.py --city Pune --profiles tomatoes cement --deep
Credits: about 4 per profile (1 Maps, 1 marketplace, 1 Shopping, 1 transport);
--deep runs every Maps query for the profile.
"""
import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bulkbeacon.normalizer import (dedupe, maps_to_suppliers,
                                   marketplace_to_suppliers, shopping_to_suppliers)
from bulkbeacon.profiles import load_profiles
from bulkbeacon.serpapi_client import SerpApiClient

REPORT = Path(__file__).resolve().parent.parent / "fixtures" / "day1_report.md"


def pct(n, d):
    return f"{round(100 * n / d)}%" if d else "n/a"


def analyse_profile(client, p, city, deep):
    lines, stats = [], {}
    maps_queries = p["maps_queries"] if deep else p["maps_queries"][:1]
    maps = []
    for q in maps_queries:
        data = client.search(engine="google_maps", type="search", q=q.format(city=city))
        maps += maps_to_suppliers(data)
    maps = dedupe(maps)
    n = len(maps)
    stats["maps"] = n
    stats["phone_pct"] = (sum(1 for s in maps if s.phone) / n) if n else 0
    reviews = [s.review_count for s in maps]
    lines.append(f"### {p['name']} (`{p['id']}`)")
    lines.append(f"- Maps: **{n}** unique places | phone {pct(sum(1 for s in maps if s.phone), n)} | "
                 f"website {pct(sum(1 for s in maps if s.website), n)} | "
                 f"median reviews {statistics.median(reviews) if reviews else 'n/a'}")
    for s in maps[:5]:
        lines.append(f"  - {s.name} ({s.category or 'type n/a'}), rating {s.rating}, {s.review_count} reviews")

    mk = marketplace_to_suppliers(client.search(
        engine="google", q=f"site:{p['marketplace_domain']} " + p["marketplace_queries"][0].format(city=city),
        location=f"{city}, India"), p["marketplace_domain"])
    stats["market"] = len(mk)
    lines.append(f"- Marketplace ({p['marketplace_domain']}): **{len(mk)}** listings")
    for s in mk[:3]:
        lines.append(f"  - {s.name}")

    shop = shopping_to_suppliers(client.search(engine="google_shopping", q=p["shopping_query"],
                                               location=f"{city}, India"))
    prices = [s.unit_price for s in shop if s.unit_price]
    stats["shop_prices"] = len(prices)
    lines.append(f"- Shopping: **{len(shop)}** results, {len(prices)} with price" +
                 (f" (min {min(prices)}, median {statistics.median(prices)}, max {max(prices)})" if prices else ""))

    tr = maps_to_suppliers(client.search(engine="google_maps", type="search",
                                         q=p["logistics_query"].format(city=city)))
    stats["transport"] = len(tr)
    lines.append(f"- Transport (Maps): **{len(tr)}** providers")

    # Rough heuristic, thresholds are our own assumptions; read the lists above yourself.
    score = (n >= 8) + (stats["phone_pct"] >= 0.6) + (len(mk) >= 3) + (len(tr) >= 5) + (len(prices) >= 3)
    stats["score"] = score
    lines.append(f"- Heuristic data score: **{score}/5** (always eyeball the names above for relevance)\n")
    return lines, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", required=True)
    ap.add_argument("--profiles", nargs="*", help="profile ids; default = all")
    ap.add_argument("--deep", action="store_true", help="run all Maps queries per profile")
    a = ap.parse_args()

    client = SerpApiClient()
    profiles = load_profiles(a.profiles)
    report, ranking = [f"# Day 1 data report: {a.city}\n"], []
    for pid, p in profiles.items():
        print(f"Testing {pid} ...")
        try:
            lines, stats = analyse_profile(client, p, a.city, a.deep)
        except Exception as e:  # keep going so one failure doesn't waste credits already spent
            print(f"  failed: {type(e).__name__}: {e}")
            report.append(f"### {pid}\n- FAILED: {type(e).__name__}: {e}\n")
            continue
        report += lines
        ranking.append((stats["score"], pid))

    ranking.sort(reverse=True)
    report.append("## Ranking by heuristic score\n" + "\n".join(f"{i+1}. {pid} ({sc}/5)" for i, (sc, pid) in enumerate(ranking)))
    text = "\n".join(report)
    REPORT.write_text(text, encoding="utf-8")
    print("\n" + text)
    print(f"\nReal SerpApi calls this run: {client.network_calls} | cache hits: {client.cache_hits} | "
          f"calls made from this machine this month: {client.credits_used_this_month()}")
    print(f"Report saved to {REPORT}")


if __name__ == "__main__":
    main()
'''
FILES['tests/test_core.py'] = r'''import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bulkbeacon import serpapi_client as sc
from bulkbeacon.normalizer import dedupe, maps_to_suppliers, marketplace_to_suppliers, shopping_to_suppliers
from bulkbeacon.profiles import load_profiles

MAPS = {"local_results": [
    {"title": "Shree Traders", "phone": "+91 98 1", "rating": 4.4, "reviews": 120, "type": "Wholesaler",
     "address": "Market Yard", "gps_coordinates": {"latitude": 18.5, "longitude": 73.8}},
    {"title": "Shree Traders", "phone": "+9198 1", "rating": 4.4, "reviews": 120},  # duplicate phone
    {"title": "No Phone Shop"}]}


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.client = sc.SerpApiClient(api_key="k", demo=False, max_calls=2, cache_dir=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _fake(self, payload):
        r = mock.Mock(); r.json.return_value = payload; r.raise_for_status.return_value = None
        return r

    def test_cache_prevents_second_call(self):
        with mock.patch.object(sc.requests, "get", return_value=self._fake(MAPS)) as g, \
             mock.patch.object(sc.SerpApiClient, "_bump_credits"):
            self.client.search(engine="google_maps", q="a")
            self.client.search(engine="google_maps", q="a")
        self.assertEqual(g.call_count, 1)
        self.assertEqual(self.client.cache_hits, 1)

    def test_call_cap(self):
        with mock.patch.object(sc.requests, "get", return_value=self._fake({})), \
             mock.patch.object(sc.SerpApiClient, "_bump_credits"):
            self.client.search(engine="google", q="1")
            self.client.search(engine="google", q="2")
            with self.assertRaises(sc.CallCapReached):
                self.client.search(engine="google", q="3")

    def test_demo_mode_never_hits_network(self):
        demo = sc.SerpApiClient(api_key="", demo=True, cache_dir=self.tmp.name)
        with mock.patch.object(sc.requests, "get") as g:
            with self.assertRaises(sc.DemoModeMiss):
                demo.search(engine="google", q="x")
        g.assert_not_called()

    def test_key_ignores_api_key(self):
        a = sc.SerpApiClient._key({"q": "x", "api_key": "1"})
        b = sc.SerpApiClient._key({"q": "x", "api_key": "2"})
        self.assertEqual(a, b)


class NormalizerTests(unittest.TestCase):
    def test_maps_and_dedupe(self):
        s = maps_to_suppliers(MAPS)
        self.assertEqual(len(s), 3)
        self.assertEqual(s[0].lat, 18.5)
        self.assertEqual(len(dedupe(s)), 2)

    def test_marketplace_filters_domain(self):
        data = {"organic_results": [{"title": "A", "link": "https://dir.indiamart.com/x"},
                                    {"title": "B", "link": "https://example.com/y"}]}
        self.assertEqual([s.name for s in marketplace_to_suppliers(data)], ["A"])

    def test_shopping_price(self):
        s = shopping_to_suppliers({"shopping_results": [{"source": "Shop", "extracted_price": 49.0}]})
        self.assertEqual(s[0].unit_price, 49.0)


class ProfileTests(unittest.TestCase):
    def test_profiles_have_required_fields(self):
        profiles = load_profiles()
        self.assertGreaterEqual(len(profiles), 3)
        for p in profiles.values():
            for k in ("id", "maps_queries", "marketplace_queries", "shopping_query", "rfq_fields"):
                self.assertIn(k, p)
            self.assertIn("{city}", p["maps_queries"][0])


if __name__ == "__main__":
    unittest.main()
'''


def main():
    base = pathlib.Path.cwd()
    created, skipped = [], []
    for rel, content in FILES.items():
        path = base / rel
        if path.exists():
            skipped.append(rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        created.append(rel)
    print(f"Created {len(created)} files, skipped {len(skipped)} existing files in {base}")
    for rel in created:
        print("  + " + rel)
    for rel in skipped:
        print("  = " + rel + " (already existed, not changed)")
    if not (base / ".env").exists():
        print("\nNext: copy .env.example to .env yourself and add your key. This script never writes keys.")


if __name__ == "__main__":
    sys.exit(main())