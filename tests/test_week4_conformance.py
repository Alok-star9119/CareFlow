import pandas as pd
import pytest
from week4_conformance import REFERENCE_PATHWAY, evaluate_conformance, summarize_conformance


def event_log(traces):
    rows = []
    for case_id, trace in traces.items():
        for i, activity in enumerate(trace):
            rows.append({"Case_ID": case_id, "Activity_Name": activity,
                         "Timestamp": f"2026-01-01 08:{i:02d}:00", "Age_Band": "Adult",
                         "Department": "ED", "Resource_ID": "R1"})
    return pd.DataFrame(rows)


def test_exact_reference_trace_conforms():
    result = evaluate_conformance(event_log({"A": REFERENCE_PATHWAY}))
    assert result.loc[0, "Conforms_To_Baseline"]
    assert result.loc[0, "Deviation_Detail"] == "None"


def test_extra_activity_is_flagged():
    trace = REFERENCE_PATHWAY[:4] + ["Triage"] + REFERENCE_PATHWAY[4:]
    result = evaluate_conformance(event_log({"A": trace}))
    assert result.loc[0, "Deviation_Flag"]
    assert "observed 'Triage'" in result.loc[0, "Deviation_Detail"]


def test_missing_activity_is_flagged():
    trace = REFERENCE_PATHWAY[:3] + REFERENCE_PATHWAY[4:]
    result = evaluate_conformance(event_log({"A": trace}))
    assert result.loc[0, "Deviation_Flag"]


def test_grouped_summary_drilldown():
    data = event_log({"A": REFERENCE_PATHWAY, "B": REFERENCE_PATHWAY[:-1]})
    conf = evaluate_conformance(data)
    summary = summarize_conformance(conf, data, ["Age_Band"])
    assert summary.loc[0, "Patient_Cases"] == 2
    assert summary.loc[0, "Deviation_Cases"] == 1


def test_missing_drilldown_column_has_clear_error():
    data = event_log({"A": REFERENCE_PATHWAY})
    conf = evaluate_conformance(data)
    with pytest.raises(ValueError, match="not found"):
        summarize_conformance(conf, data, ["Doctor_Name"])


def test_invalid_timestamp_rejected():
    data = event_log({"A": REFERENCE_PATHWAY})
    data.loc[0, "Timestamp"] = "not-a-time"
    with pytest.raises(ValueError, match="Timestamp"):
        evaluate_conformance(data)
