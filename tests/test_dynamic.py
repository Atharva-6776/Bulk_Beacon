
import unittest
from bulkbeacon.profiles import get_profile
from bulkbeacon.schemas import Request, ProductProfile

class TestDynamicProfile(unittest.TestCase):
    def test_dynamic_profile_generation(self):
        profile = get_profile("industrial vibration sensors")
        self.assertEqual(profile.id, "industrial_vibration_sensors")
        self.assertEqual(profile.category, "other")
        self.assertIn("industrial vibration sensors wholesale supplier {city}", profile.maps_queries)
        
    def test_curated_profile(self):
        profile = get_profile("cement")
        self.assertEqual(profile.id, "cement")
        self.assertTrue("cement dealer {city}" in profile.maps_queries)

class TestUnits(unittest.TestCase):
    def test_request_unit(self):
        req = Request(raw_text="300 meters PVC pipe", item="PVC pipe", quantity=300, unit="meter")
        self.assertEqual(req.unit, "meter")
        self.assertEqual(req.item, "PVC pipe")

if __name__ == "__main__":
    unittest.main()
