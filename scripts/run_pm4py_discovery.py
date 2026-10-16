#!/usr/bin/env python3
"""Discover CareFlow process flows from a normalized event-log CSV.

Always exports transparent pandas-based artifacts. If PM4Py is installed, also exports
PM4Py DFG/start/end activity results and an inductively discovered Petri net (PNML).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

REQUIRED_COLUMNS = ["Case_ID", "Activity_Name", "Timestamp"]
IDEAL_PATH = [
    "Registration", "Triage", "Physician Assessment", "X-Ray",
    "Physician Reassessment", "Treatment", "Discharge",
]


def load_events(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Event-log CSV not found: {path}")
    events = pd.read_csv(path)
    missing = sorted(set(REQUIRED_COLUMNS) - set(events.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    events = events.rename(columns={
        "Case_ID": "case_id",
        "Activity_Name": "activity_name",
        "Timestamp": "event_timestamp",
    })
    events["event_timestamp"] = pd.to_datetime(events["event_timestamp"], errors="coerce")
    bad = events[["case_id", "activity_name", "event_timestamp"]].isna().any(axis=1)
    if bad.any():
        raise ValueError(f"Found {int(bad.sum())} rows with null case, activity, or invalid timestamp.")
    events["case_id"] = events["case_id"].astype(str).str.strip()
    events["activity_name"] = events["activity_name"].astype(str).str.strip()
    if (events["case_id"] == "").any() or (events["activity_name"] == "").any():
        raise ValueError("Case IDs and activity names cannot be blank.")
    return events.sort_values(["case_id", "event_timestamp"], kind="stable").reset_index(drop=True)


def export_native_artifacts(events: pd.DataFrame, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    ordered = events.sort_values(["case_id", "event_timestamp"], kind="stable").copy()
    ordered["next_activity"] = ordered.groupby("case_id")["activity_name"].shift(-1)
    transitions = (
        ordered.dropna(subset=["next_activity"])
        .groupby(["activity_name", "next_activity"], as_index=False)
        .size()
        .rename(columns={"size": "frequency"})
        .sort_values("frequency", ascending=False)
    )
    transitions.to_csv(out_dir / "native_directly_follows.csv", index=False)

    def format_trace(values: list[str]) -> str:
        return " → ".join(values)

    case_rows = []
    for case_id, group in ordered.groupby("case_id", sort=False):
        trace = group["activity_name"].tolist()
        duration = (group["event_timestamp"].iloc[-1] - group["event_timestamp"].iloc[0]).total_seconds() / 60
        returned = any(a == "X-Ray" and b == "Triage" for a, b in zip(trace, trace[1:]))
        case_rows.append({
            "case_id": case_id,
            "case_trace": format_trace(trace),
            "case_throughput_minutes": round(duration, 2),
            "returned_to_triage_after_xray": returned,
            "conforms_to_baseline": trace == IDEAL_PATH,
            "deviation_reason": "Rework loop: X-Ray → Triage" if returned else (
                "No deviation from the reference sequence" if trace == IDEAL_PATH else "Other sequence deviation — review"
            ),
        })
    case_df = pd.DataFrame(case_rows)
    case_df.to_csv(out_dir / "baseline_conformance_results.csv", index=False)
    variants = (
        case_df.groupby("case_trace", as_index=False)
        .agg(case_count=("case_id", "nunique"), mean_throughput_minutes=("case_throughput_minutes", "mean"))
    )
    variants["share_percent"] = variants["case_count"] / len(case_df) * 100 if len(case_df) else 0
    variants.sort_values("case_count", ascending=False).to_csv(out_dir / "native_process_variants.csv", index=False)

    n_returns = int(case_df["returned_to_triage_after_xray"].sum()) if len(case_df) else 0
    summary = {
        "case_count": int(case_df["case_id"].nunique()),
        "event_count": int(len(ordered)),
        "distinct_activities": int(ordered["activity_name"].nunique()),
        "process_variant_count": int(variants.shape[0]),
        "xray_to_triage_cases": n_returns,
        "xray_to_triage_rate_percent": round(100 * n_returns / len(case_df), 2) if len(case_df) else None,
        "exact_baseline_conformance_percent": round(100 * case_df["conforms_to_baseline"].mean(), 2) if len(case_df) else None,
    }
    (out_dir / "process_discovery_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def run_pm4py(events: pd.DataFrame, out_dir: Path) -> bool:
    try:
        import pm4py
    except ImportError:
        return False

    pm_events = events[["case_id", "activity_name", "event_timestamp"]].rename(columns={
        "case_id": "case:concept:name",
        "activity_name": "concept:name",
        "event_timestamp": "time:timestamp",
    }).copy()
    pm_events["time:timestamp"] = pd.to_datetime(pm_events["time:timestamp"], errors="raise")
    pm_events = pm_events.sort_values(["case:concept:name", "time:timestamp"], kind="stable")

    dfg, start_activities, end_activities = pm4py.discover_dfg(pm_events)
    dfg_rows = [
        {"source_activity": str(source), "target_activity": str(target), "frequency": int(count)}
        for (source, target), count in dfg.items()
    ]
    pd.DataFrame(dfg_rows, columns=["source_activity", "target_activity", "frequency"]).sort_values(
        "frequency", ascending=False
    ).to_csv(out_dir / "pm4py_directly_follows.csv", index=False)
    pd.DataFrame([{"activity": str(activity), "frequency": int(count)} for activity, count in start_activities.items()]).to_csv(
        out_dir / "pm4py_start_activities.csv", index=False
    )
    pd.DataFrame([{"activity": str(activity), "frequency": int(count)} for activity, count in end_activities.items()]).to_csv(
        out_dir / "pm4py_end_activities.csv", index=False
    )

    net, initial_marking, final_marking = pm4py.discover_petri_net_inductive(pm_events)
    pnml_path = out_dir / "pm4py_inductive_process_model.pnml"
    pm4py.write_pnml(net, initial_marking, final_marking, str(pnml_path))
    (out_dir / "pm4py_model_summary.json").write_text(json.dumps({
        "places": len(net.places),
        "transitions": len(net.transitions),
        "arcs": len(net.arcs),
        "pnml_file": pnml_path.name,
        "note": "Inductively discovered model from the supplied event log; not a clinically approved care pathway.",
    }, indent=2), encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="?", default="careflow_data/clean_event_log.csv", help="Normalized event-log CSV")
    parser.add_argument("--output-dir", default="careflow_data/process_discovery", help="Output directory")
    parser.add_argument("--require-pm4py", action="store_true", help="Return nonzero if PM4Py is unavailable")
    args = parser.parse_args()

    try:
        events = load_events(Path(args.csv))
        out_dir = Path(args.output_dir)
        summary = export_native_artifacts(events, out_dir)
        print("Native event-log analysis complete:")
        print(json.dumps(summary, indent=2))
        if run_pm4py(events, out_dir):
            print(f"PM4Py DFG and inductive Petri-net model exported to: {out_dir.resolve()}")
        else:
            print("PM4Py is not installed; native DFG, variants, and baseline-conformance exports are still available.")
            if args.require_pm4py:
                print("Install the dependencies in requirements-cloud.txt (or requirements.txt) and rerun.", file=sys.stderr)
                return 2
        return 0
    except Exception as exc:
        print(f"Process discovery failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
