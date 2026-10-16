#!/usr/bin/env python3
"""Audit a CareFlow event-log CSV before it enters the warehouse/process-mining pipeline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

REQUIRED_COLUMNS = {"Case_ID", "Activity_Name", "Timestamp"}
EXPECTED_BOUNDARIES = ("Registration", "Discharge")


def audit_event_log(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Event log not found: {path}")
    frame = pd.read_csv(path)
    missing_columns = sorted(REQUIRED_COLUMNS - set(frame.columns))
    report = {
        "file": str(path),
        "row_count": int(len(frame)),
        "case_count": int(frame["Case_ID"].nunique(dropna=True)) if "Case_ID" in frame else 0,
        "missing_required_columns": missing_columns,
        "null_required_values": {},
        "invalid_timestamps": None,
        "duplicate_event_keys": None,
        "non_monotonic_cases": [],
        "missing_registration_cases": [],
        "missing_discharge_cases": [],
        "xray_to_triage_cases": 0,
        "xray_to_triage_rate_percent": None,
        "passed": False,
    }
    if missing_columns:
        return report

    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    report["null_required_values"] = {
        col: int(frame[col].isna().sum()) for col in ["Case_ID", "Activity_Name", "Timestamp"]
    }
    report["invalid_timestamps"] = int(frame["Timestamp"].isna().sum())
    report["duplicate_event_keys"] = int(
        frame.duplicated(subset=["Case_ID", "Activity_Name", "Timestamp", *(["Resource_ID"] if "Resource_ID" in frame else [])]).sum()
    )

    source_valid = frame.dropna(subset=["Case_ID", "Activity_Name", "Timestamp"]).copy()
    out_of_order = []
    for case_id, group in source_valid.groupby("Case_ID", sort=False):
        if (group["Timestamp"].diff().dropna() < pd.Timedelta(0)).any():
            out_of_order.append(str(case_id))
    report["non_monotonic_cases"] = out_of_order

    # Re-order before process analysis: event-file row order is not itself a process guarantee.
    valid = source_valid.sort_values(["Case_ID", "Timestamp"], kind="stable")
    if len(valid):
        delta = valid.groupby("Case_ID", sort=False)["Timestamp"].diff()
        # Sorting should make this impossible, but it detects bad/ambiguous equal timestamps as a separate review item.
        equal_timestamp_rows = valid.duplicated(subset=["Case_ID", "Timestamp"], keep=False)
        report["equal_timestamp_event_rows"] = int(equal_timestamp_rows.sum())
        report["non_positive_timestamp_step_rows"] = int((delta <= pd.Timedelta(0)).fillna(False).sum())

    traces = valid.groupby("Case_ID", sort=False)["Activity_Name"].agg(list)
    report["missing_registration_cases"] = [str(case) for case, trace in traces.items() if not trace or trace[0] != EXPECTED_BOUNDARIES[0]]
    report["missing_discharge_cases"] = [str(case) for case, trace in traces.items() if not trace or trace[-1] != EXPECTED_BOUNDARIES[1]]
    returned = 0
    for trace in traces:
        if any(left == "X-Ray" and right == "Triage" for left, right in zip(trace, trace[1:])):
            returned += 1
    report["xray_to_triage_cases"] = returned
    report["xray_to_triage_rate_percent"] = round(100 * returned / len(traces), 2) if len(traces) else None

    hard_fail = (
        any(report["null_required_values"].values())
        or report["invalid_timestamps"] > 0
        or report["duplicate_event_keys"] > 0
        or report.get("non_positive_timestamp_step_rows", 0) > 0
        or bool(report["missing_registration_cases"])
        or bool(report["missing_discharge_cases"])
    )
    report["passed"] = not hard_fail
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="?", default="careflow_data/clean_event_log.csv", help="Path to the normalized event-log CSV")
    parser.add_argument("--json-out", default="careflow_data/event_log_audit.json", help="Where to write the audit report")
    args = parser.parse_args()

    report = audit_event_log(Path(args.csv))
    output_path = Path(args.json_out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nAudit {'PASSED' if report['passed'] else 'FAILED'} — report: {output_path}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
