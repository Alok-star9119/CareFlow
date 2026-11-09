"""Week 4 conformance and drill-down analytics for the CareFlow prototype.

The exact-sequence baseline is a transparent demonstration rule, not a clinical
standard. Use synthetic data unless authorized, de-identified data is approved.
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

REQUIRED_COLUMNS = ["Case_ID", "Activity_Name", "Timestamp"]
REFERENCE_PATHWAY = [
    "Registration", "Triage", "Physician Assessment", "X-Ray",
    "Physician Reassessment", "Treatment", "Discharge",
]


def _validated_copy(event_log: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(event_log, pd.DataFrame):
        raise TypeError("Event log must be a pandas DataFrame.")
    missing = [c for c in REQUIRED_COLUMNS if c not in event_log.columns]
    if missing:
        raise ValueError("Missing required column(s): " + ", ".join(missing))
    if event_log.empty:
        raise ValueError("Event log is empty; provide at least one event.")
    data = event_log.copy()
    for col in ("Case_ID", "Activity_Name"):
        bad = data[col].isna() | data[col].astype("string").str.strip().eq("").fillna(True)
        if bad.any():
            raise ValueError(f"Column '{col}' contains blank or missing values.")
        data[col] = data[col].astype(str).str.strip()
    data["Timestamp"] = pd.to_datetime(data["Timestamp"], errors="coerce", format="mixed")
    if data["Timestamp"].isna().any():
        raise ValueError("Column 'Timestamp' contains invalid or missing timestamps.")
    return data.sort_values(["Case_ID", "Timestamp"], kind="stable").reset_index(drop=True)


def evaluate_conformance(event_log: pd.DataFrame, reference_pathway: list[str] | None = None) -> pd.DataFrame:
    """Return one row per case with exact trace-match status and deviation details."""
    data = _validated_copy(event_log)
    baseline = list(reference_pathway or REFERENCE_PATHWAY)
    if not baseline:
        raise ValueError("Reference pathway must contain at least one activity.")
    rows = []
    for case_id, group in data.groupby("Case_ID", sort=True):
        trace = group["Activity_Name"].tolist()
        matched = trace == baseline
        mismatch_index = next((i for i, pair in enumerate(zip(trace, baseline)) if pair[0] != pair[1]), None)
        if mismatch_index is None and len(trace) != len(baseline):
            mismatch_index = min(len(trace), len(baseline))
        if matched:
            deviation = "None"
        elif mismatch_index is not None and mismatch_index < len(trace) and mismatch_index < len(baseline):
            deviation = f"Expected '{baseline[mismatch_index]}', observed '{trace[mismatch_index]}' at position {mismatch_index + 1}"
        elif len(trace) > len(baseline):
            deviation = f"Unexpected extra activity '{trace[len(baseline)]}' at position {len(baseline) + 1}"
        else:
            deviation = f"Trace ended after {len(trace)} event(s); expected {len(baseline)}"
        rows.append({
            "Case_ID": case_id,
            "Event_Count": len(trace),
            "Observed_Trace": " → ".join(trace),
            "Conforms_To_Baseline": bool(matched),
            "Deviation_Flag": not matched,
            "Deviation_Detail": deviation,
            "First_Event_Timestamp": group["Timestamp"].iloc[0],
            "Last_Event_Timestamp": group["Timestamp"].iloc[-1],
            "Case_Duration_Minutes": (group["Timestamp"].iloc[-1] - group["Timestamp"].iloc[0]).total_seconds() / 60,
        })
    return pd.DataFrame(rows)


def summarize_conformance(conformance: pd.DataFrame, event_log: pd.DataFrame,
                          group_columns: list[str] | None = None) -> pd.DataFrame:
    """Summarize conformance KPIs overall or by optional case-level fields."""
    group_columns = group_columns or []
    cases = conformance.copy()
    if group_columns:
        missing = [c for c in group_columns if c not in event_log.columns]
        if missing:
            raise ValueError("Requested drill-down column(s) not found: " + ", ".join(missing))
        case_dims = event_log.sort_values("Timestamp").groupby("Case_ID", as_index=False).first()[["Case_ID", *group_columns]]
        cases = cases.merge(case_dims, on="Case_ID", how="left", validate="one_to_one")
        for col in group_columns:
            cases[col] = cases[col].fillna("Unknown")
    grouped = cases.groupby(group_columns, dropna=False) if group_columns else [("Overall", cases)]
    rows = []
    for key, part in grouped:
        keys = key if isinstance(key, tuple) else (key,) if group_columns else ()
        row = {col: val for col, val in zip(group_columns, keys)}
        total = len(part)
        deviations = int(part["Deviation_Flag"].sum())
        row.update({
            "Patient_Cases": total,
            "Conforming_Cases": int(part["Conforms_To_Baseline"].sum()),
            "Deviation_Cases": deviations,
            "Conformance_Rate_Percent": round(100 * (total - deviations) / total, 2) if total else 0.0,
            "Deviation_Rate_Percent": round(100 * deviations / total, 2) if total else 0.0,
            "Mean_Case_Duration_Minutes": round(float(part["Case_Duration_Minutes"].mean()), 2) if total else 0.0,
        })
        rows.append(row)
    return pd.DataFrame(rows)


def run_week4(input_csv: str | Path, output_dir: str | Path) -> dict:
    """Run conformance analysis and export drill-down-ready CSV/JSON artifacts."""
    input_csv, output_dir = Path(input_csv), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(input_csv)
    data = _validated_copy(raw)
    conformance = evaluate_conformance(data)
    outputs = {}
    outputs["case_results"] = output_dir / "week4_conformance_by_case.csv"
    conformance.to_csv(outputs["case_results"], index=False)
    outputs["overall_summary"] = output_dir / "week4_conformance_summary.csv"
    summarize_conformance(conformance, data).to_csv(outputs["overall_summary"], index=False)
    for column in ("Department", "Resource_ID", "Age_Band", "Arrival_Shift"):
        if column in data.columns:
            path = output_dir / f"week4_conformance_by_{column.lower()}.csv"
            summarize_conformance(conformance, data, [column]).to_csv(path, index=False)
            outputs[f"by_{column.lower()}"] = path
    summary = {
        "input_file": str(input_csv),
        "case_count": int(len(conformance)),
        "conforming_cases": int(conformance["Conforms_To_Baseline"].sum()),
        "deviation_cases": int(conformance["Deviation_Flag"].sum()),
        "conformance_rate_percent": round(100 * float(conformance["Conforms_To_Baseline"].mean()), 2),
        "baseline": REFERENCE_PATHWAY,
        "baseline_rule": "Exact activity-sequence match; demonstration rule only",
        "synthetic_data_notice": "Do not interpret prototype results as real hospital performance evidence.",
        "outputs": {key: str(value) for key, value in outputs.items()},
    }
    json_path = output_dir / "week4_kpi_summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary["json_summary"] = str(json_path)
    return summary

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run CareFlow Week 4 baseline conformance checks.")
    parser.add_argument("--input", default="careflow_data/clean_event_log.csv")
    parser.add_argument("--output-dir", default="careflow_data/week4_outputs")
    args = parser.parse_args()
    print(json.dumps(run_week4(args.input, args.output_dir), indent=2))
