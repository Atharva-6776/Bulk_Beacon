import json
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

    def test_dynamic_profile(self):
        from bulkbeacon.profiles import get_profile
        
        # Test existing profile
        p_cement = get_profile("cement")
        self.assertEqual(p_cement.id, "cement")
        self.assertFalse(p_cement.is_dynamic)

        # Test dynamic fallback
        p_unknown = get_profile("Unobtanium")
        self.assertEqual(p_unknown.id, "unobtanium")
        self.assertTrue(p_unknown.is_dynamic)
        self.assertIn("Unobtanium", p_unknown.maps_queries[0])


if __name__ == "__main__":
    unittest.main()
