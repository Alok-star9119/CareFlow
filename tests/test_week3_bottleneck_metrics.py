import pandas as pd
import pytest

from week3_bottleneck_metrics import (
    build_transition_metrics, build_case_metrics, load_event_log
)


def sample_events():
    return pd.DataFrame({
        "Case_ID": ["C1", "C1", "C1", "C2", "C2"],
        "Activity_Name": ["Registration", "X-Ray", "Triage", "Registration", "Discharge"],
        "Timestamp": pd.to_datetime([
            "2026-01-01 09:00", "2026-01-01 09:10", "2026-01-01 09:25",
            "2026-01-01 10:00", "2026-01-01 10:40"
        ])
    })


def test_transition_metrics_calculate_elapsed_minutes():
    result = build_transition_metrics(sample_events())
    row = result[(result["From_Activity"] == "X-Ray") & (result["To_Activity"] == "Triage")].iloc[0]
    assert row["Transition_Count"] == 1
    assert row["Mean_Wait_Minutes"] == 15.0


def test_case_metrics_detect_loopback_once_per_case():
    result = build_case_metrics(sample_events()).set_index("Case_ID")
    assert bool(result.loc["C1", "XRay_To_Triage_Loopback"]) is True
    assert bool(result.loc["C2", "XRay_To_Triage_Loopback"]) is False
    assert result.loc["C1", "Case_Duration_Minutes"] == 25.0


def test_load_event_log_rejects_missing_columns(tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame({"Case_ID": ["C1"]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="Missing required columns"):
        load_event_log(path)


def test_load_event_log_rejects_invalid_timestamp(tmp_path):
    path = tmp_path / "bad_time.csv"
    pd.DataFrame({
        "Case_ID": ["C1"], "Activity_Name": ["Registration"], "Timestamp": ["not-a-time"]
    }).to_csv(path, index=False)
    with pytest.raises(ValueError, match="Invalid required values"):
        load_event_log(path)


def test_transition_metrics_empty_single_event_case():
    events = pd.DataFrame({
        "Case_ID": ["C1"], "Activity_Name": ["Registration"],
        "Timestamp": pd.to_datetime(["2026-01-01 09:00"])
    })
    result = build_transition_metrics(events)
    assert result.empty
