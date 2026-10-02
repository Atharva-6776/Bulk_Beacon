"""SerpApi client with disk cache, credit counter and demo mode.

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
