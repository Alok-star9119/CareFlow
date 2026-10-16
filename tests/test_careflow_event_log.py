from pathlib import Path
import unittest

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "careflow_data" / "clean_event_log.csv"


class CareFlowEventLogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = pd.read_csv(DATA_PATH)
        cls.events["Timestamp"] = pd.to_datetime(cls.events["Timestamp"], errors="raise")

    def test_core_columns_exist_and_are_populated(self):
        required = ["Case_ID", "Activity_Name", "Timestamp"]
        self.assertTrue(set(required).issubset(self.events.columns))
        self.assertFalse(self.events[required].isna().any().any())

    def test_each_case_is_chronological(self):
        for _, group in self.events.sort_values(["Case_ID", "Timestamp"]).groupby("Case_ID"):
            self.assertTrue(group["Timestamp"].is_monotonic_increasing)

    def test_complete_demo_cases_have_registration_and_discharge(self):
        for _, group in self.events.sort_values(["Case_ID", "Timestamp"]).groupby("Case_ID"):
            activities = group["Activity_Name"].tolist()
            self.assertEqual(activities[0], "Registration")
            self.assertEqual(activities[-1], "Discharge")

    def test_expected_synthetic_loopback_scenario(self):
        cases = 0
        returns = 0
        ordered = self.events.sort_values(["Case_ID", "Timestamp"])
        for _, group in ordered.groupby("Case_ID"):
            activities = group["Activity_Name"].tolist()
            cases += 1
            returns += int(any(a == "X-Ray" and b == "Triage" for a, b in zip(activities, activities[1:])))
        self.assertEqual(cases, 500)
        self.assertEqual(returns, 200)
        self.assertAlmostEqual(returns / cases, 0.40)

    def test_demo_is_explicitly_synthetic(self):
        self.assertIn("Is_Synthetic", self.events.columns)
        normalized = self.events["Is_Synthetic"].astype(str).str.lower()
        self.assertTrue(normalized.isin(["true", "1", "yes"]).all())


if __name__ == "__main__":
    unittest.main()
