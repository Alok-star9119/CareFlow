import json
import pandas as pd
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "careflow_data" / "clean_event_log.csv"


def test_dashboard_case_builder_matches_known_rates():
    from build_dashboard import build_cases
    cases = build_cases(DATA)
    assert len(cases) == 500
    assert sum(c["loop"] for c in cases) == 200
    assert sum(c["conf"] for c in cases) == 300


def test_dashboard_html_is_written(tmp_path):
    from build_dashboard import TEMPLATE, build_cases
    out = tmp_path / "d.html"
    out.write_text(TEMPLATE.replace("__DATA__", json.dumps(build_cases(DATA))), encoding="utf-8")
    assert "CareFlow" in out.read_text(encoding="utf-8")
    assert "__DATA__" not in out.read_text(encoding="utf-8")


def test_pm4py_alignment_conformance(tmp_path):
    pytest.importorskip("pm4py")
    from run_pm4py_conformance import run
    summary = run(DATA, tmp_path)
    assert summary["cases"] == 500
    assert summary["baseline_conforming_cases"] == 300
    assert (tmp_path / "pm4py_alignment_by_case.csv").exists()
