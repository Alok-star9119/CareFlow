from pathlib import Path
import json
import sys
import tempfile
import unittest

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from audit_event_log import audit_event_log  # noqa: E402
from run_pm4py_discovery import export_native_artifacts, load_events  # noqa: E402


class PipelineScriptTests(unittest.TestCase):
    def test_audit_passes_for_current_synthetic_log(self):
        report = audit_event_log(PROJECT_ROOT / "careflow_data" / "clean_event_log.csv")
        self.assertTrue(report["passed"])
        self.assertEqual(report["case_count"], 500)
        self.assertEqual(report["xray_to_triage_cases"], 200)

    def test_process_discovery_native_exports_are_created(self):
        events = load_events(PROJECT_ROOT / "careflow_data" / "clean_event_log.csv")
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            summary = export_native_artifacts(events, output)
            self.assertEqual(summary["event_count"], 3900)
            self.assertEqual(summary["process_variant_count"], 2)
            self.assertAlmostEqual(summary["xray_to_triage_rate_percent"], 40.0)
            self.assertTrue((output / "native_directly_follows.csv").is_file())
            self.assertTrue((output / "native_process_variants.csv").is_file())
            self.assertTrue((output / "baseline_conformance_results.csv").is_file())
            saved = json.loads((output / "process_discovery_summary.json").read_text())
            self.assertEqual(saved["case_count"], 500)

    def test_dbt_project_and_model_files_exist(self):
        dbt_dir = PROJECT_ROOT / "careflow_dbt"
        self.assertTrue((dbt_dir / "dbt_project.yml").is_file())
        self.assertTrue((dbt_dir / "profiles.yml.example").is_file())
        expected_models = [
            "stg_careflow__events.sql",
            "int_careflow__ordered_events.sql",
            "int_careflow__event_transitions.sql",
            "fct_patient_cases.sql",
            "fct_transition_bottlenecks.sql",
            "fct_triage_loopbacks.sql",
            "fct_process_variants.sql",
            "fct_conformance_results.sql",
        ]
        all_models = {p.name for p in (dbt_dir / "models").rglob("*.sql")}
        self.assertTrue(set(expected_models).issubset(all_models))


if __name__ == "__main__":
    unittest.main()
