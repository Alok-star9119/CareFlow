#!/usr/bin/env python3
"""Create Week 3 CareFlow bottleneck metrics and BI-ready CSV summaries.

Input must be a normalized event log with Case_ID, Activity_Name and Timestamp.
Optional fields such as Arrival_Shift and Department are retained for grouping.
All outputs describe the supplied dataset; synthetic results are not clinical evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import pandas as pd

REQUIRED = {"Case_ID", "Activity_Name", "Timestamp"}


def load_event_log(path: Path) -> pd.DataFrame:
    """Read, validate, normalize and chronologically sort event records."""
    if not path.is_file():
        raise FileNotFoundError(f"Event-log CSV not found: {path}")
    frame = pd.read_csv(path)
    missing = sorted(REQUIRED - set(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    frame["Case_ID"] = frame["Case_ID"].astype("string").str.strip()
    frame["Activity_Name"] = frame["Activity_Name"].astype("string").str.strip()
    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    invalid = frame[["Case_ID", "Activity_Name", "Timestamp"]].isna().any(axis=1)
    blanks = frame["Case_ID"].eq("") | frame["Activity_Name"].eq("")
    if invalid.any() or blanks.any():
        raise ValueError(f"Invalid required values found: {int((invalid | blanks).sum())} row(s).")
    frame = frame.sort_values(["Case_ID", "Timestamp"], kind="stable").reset_index(drop=True)
    return frame


def build_transition_metrics(events: pd.DataFrame) -> pd.DataFrame:
    """Summarize case-to-case consecutive activity transitions and elapsed minutes."""
    ordered = events.sort_values(["Case_ID", "Timestamp"], kind="stable").copy()
    grouped = ordered.groupby("Case_ID", sort=False)
    ordered["Next_Activity"] = grouped["Activity_Name"].shift(-1)
    ordered["Next_Timestamp"] = grouped["Timestamp"].shift(-1)
    ordered["Wait_Minutes"] = (
        ordered["Next_Timestamp"] - ordered["Timestamp"]
    ).dt.total_seconds() / 60
    steps = ordered.dropna(subset=["Next_Activity"]).copy()
    steps = steps[steps["Wait_Minutes"] >= 0]
    if steps.empty:
        return pd.DataFrame(columns=[
            "From_Activity", "To_Activity", "Transition_Count",
            "Mean_Wait_Minutes", "Median_Wait_Minutes", "P90_Wait_Minutes"
        ])
    summary = steps.groupby(["Activity_Name", "Next_Activity"], as_index=False).agg(
        Transition_Count=("Case_ID", "size"),
        Mean_Wait_Minutes=("Wait_Minutes", "mean"),
        Median_Wait_Minutes=("Wait_Minutes", "median"),
        P90_Wait_Minutes=("Wait_Minutes", lambda x: x.quantile(0.90)),
    )
    summary = summary.rename(columns={
        "Activity_Name": "From_Activity", "Next_Activity": "To_Activity"
    })
    metric_cols = ["Mean_Wait_Minutes", "Median_Wait_Minutes", "P90_Wait_Minutes"]
    summary[metric_cols] = summary[metric_cols].round(2)
    return summary.sort_values(
        ["Mean_Wait_Minutes", "Transition_Count"], ascending=[False, False]
    ).reset_index(drop=True)


def build_case_metrics(events: pd.DataFrame) -> pd.DataFrame:
    """Calculate each case's duration and identify X-Ray-to-Triage rework loops."""
    records = []
    for case_id, group in events.groupby("Case_ID", sort=False):
        group = group.sort_values("Timestamp", kind="stable")
        activities = group["Activity_Name"].tolist()
        duration = (group["Timestamp"].iloc[-1] - group["Timestamp"].iloc[0]).total_seconds() / 60
        loopback = any(a == "X-Ray" and b == "Triage" for a, b in zip(activities, activities[1:]))
        records.append({
            "Case_ID": str(case_id),
            "First_Activity": activities[0],
            "Last_Activity": activities[-1],
            "Event_Count": len(activities),
            "Case_Duration_Minutes": round(duration, 2),
            "XRay_To_Triage_Loopback": bool(loopback),
            "Case_Trace": " -> ".join(activities),
        })
    return pd.DataFrame(records)


def build_group_metrics(events: pd.DataFrame, cases: pd.DataFrame, group_column: str) -> pd.DataFrame:
    """Report case count, average duration, and loopback rate by an optional category."""
    if group_column not in events.columns:
        return pd.DataFrame(columns=[
            group_column, "Case_Count", "Mean_Duration_Minutes",
            "Loopback_Cases", "Loopback_Rate_Percent"
        ])
    mapping = events[["Case_ID", group_column]].drop_duplicates("Case_ID")
    joined = cases.merge(mapping, on="Case_ID", how="left")
    summary = joined.groupby(group_column, dropna=False, as_index=False).agg(
        Case_Count=("Case_ID", "nunique"),
        Mean_Duration_Minutes=("Case_Duration_Minutes", "mean"),
        Loopback_Cases=("XRay_To_Triage_Loopback", "sum"),
        Loopback_Rate_Percent=("XRay_To_Triage_Loopback", lambda x: 100 * x.mean()),
    )
    summary[["Mean_Duration_Minutes", "Loopback_Rate_Percent"]] = summary[
        ["Mean_Duration_Minutes", "Loopback_Rate_Percent"]
    ].round(2)
    return summary.sort_values(group_column).reset_index(drop=True)


def analyze_csv(input_path: Path, output_dir: Path) -> dict:
    """Run Week 3 metrics and export CSVs and a compact JSON KPI summary."""
    events = load_event_log(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    transitions = build_transition_metrics(events)
    cases = build_case_metrics(events)
    shifts = build_group_metrics(events, cases, "Arrival_Shift")
    transitions.to_csv(output_dir / "week3_transition_bottlenecks.csv", index=False)
    cases.to_csv(output_dir / "week3_case_metrics.csv", index=False)
    shifts.to_csv(output_dir / "week3_shift_metrics.csv", index=False)
    loopbacks = int(cases["XRay_To_Triage_Loopback"].sum()) if len(cases) else 0
    summary = {
        "case_count": int(cases["Case_ID"].nunique()),
        "event_count": int(len(events)),
        "activity_count": int(events["Activity_Name"].nunique()),
        "transition_type_count": int(len(transitions)),
        "mean_case_duration_minutes": round(float(cases["Case_Duration_Minutes"].mean()), 2) if len(cases) else None,
        "median_case_duration_minutes": round(float(cases["Case_Duration_Minutes"].median()), 2) if len(cases) else None,
        "xray_to_triage_loopback_cases": loopbacks,
        "xray_to_triage_loopback_rate_percent": round(100 * loopbacks / len(cases), 2) if len(cases) else None,
        "data_source_note": "Metrics describe the supplied event log; synthetic data is illustrative only."
    }
    (output_dir / "week3_kpi_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="careflow_data/clean_event_log.csv", help="Normalized event-log CSV")
    parser.add_argument("--output-dir", default="careflow_data/week3_metrics", help="Directory for Week 3 outputs")
    args = parser.parse_args()
    summary = analyze_csv(Path(args.input), Path(args.output_dir))
    print(json.dumps(summary, indent=2))
    print(f"Week 3 metrics exported to: {Path(args.output_dir).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
