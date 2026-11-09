#!/usr/bin/env python3
"""PM4Py token-based replay and alignment conformance for CareFlow.

Compares every patient journey against (a) a Petri net discovered from the
event log (as-is fitness) and (b) a reference Petri net built from the
documented baseline pathway (ideal-vs-actual deviations).
Synthetic data only; the baseline is a prototype rule, not a clinical standard.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
import pm4py
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils

BASELINE = ["Registration", "Triage", "Physician Assessment", "X-Ray",
            "Physician Reassessment", "Treatment", "Discharge"]


def baseline_net(activities=BASELINE):
    net, im, fm = PetriNet("baseline"), Marking(), Marking()
    places = [PetriNet.Place(f"p{i}") for i in range(len(activities) + 1)]
    for p in places:
        net.places.add(p)
    for i, act in enumerate(activities):
        t = PetriNet.Transition(f"t{i}", act)
        net.transitions.add(t)
        petri_utils.add_arc_from_to(places[i], t, net)
        petri_utils.add_arc_from_to(t, places[i + 1], net)
    im[places[0]], fm[places[-1]] = 1, 1
    return net, im, fm


def prepare(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    df = df.rename(columns={"Case_ID": "case:concept:name", "Activity_Name": "concept:name",
                            "Timestamp": "time:timestamp"})
    return pm4py.format_dataframe(df, case_id="case:concept:name", activity_key="concept:name",
                                  timestamp_key="time:timestamp").sort_values(["case:concept:name", "time:timestamp"])


def run(input_path: Path, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    log = prepare(input_path)
    disc_net, disc_im, disc_fm = pm4py.discover_petri_net_inductive(log)
    ref_net, ref_im, ref_fm = baseline_net()

    # variant-level alignments (cheap: 2 variants) then mapped back to cases
    variants = log.groupby("case:concept:name")["concept:name"].apply(tuple).rename("trace").reset_index()
    rows = []
    for trace in variants["trace"].unique():
        sub = pd.DataFrame({"case:concept:name": "v", "concept:name": list(trace),
                            "time:timestamp": pd.date_range("2026-01-01", periods=len(trace), freq="min")})
        sub = pm4py.format_dataframe(sub, case_id="case:concept:name", activity_key="concept:name",
                                     timestamp_key="time:timestamp")
        al_ref = pm4py.conformance_diagnostics_alignments(sub, ref_net, ref_im, ref_fm)[0]
        fit_ref = pm4py.fitness_alignments(sub, ref_net, ref_im, ref_fm)["average_trace_fitness"]
        fit_disc = pm4py.fitness_token_based_replay(sub, disc_net, disc_im, disc_fm)["average_trace_fitness"]
        moves = [m for m in al_ref["alignment"] if m[0] != m[1] or (m[0][0] == ">>" or m[0][1] == ">>")]
        log_only = [a[0] for a in al_ref["alignment"] if a[1] == ">>"]
        model_only = [a[1] for a in al_ref["alignment"] if a[0] == ">>"]
        rows.append({"trace": trace, "Alignment_Cost": al_ref["cost"] // 10000 if al_ref["cost"] >= 10000 else al_ref["cost"],
                     "Fitness_vs_Baseline": round(fit_ref, 4), "Fitness_vs_Discovered_Model": round(fit_disc, 4),
                     "Extra_Activities_Not_In_Baseline": " | ".join(log_only), "Missing_Baseline_Activities": " | ".join(model_only)})
    vdf = pd.DataFrame(rows)
    case_df = variants.merge(vdf, on="trace").drop(columns="trace").rename(columns={"case:concept:name": "Case_ID"})
    case_df["Conforms_To_Baseline"] = case_df["Alignment_Cost"] == 0
    case_df.sort_values("Case_ID").to_csv(out / "pm4py_alignment_by_case.csv", index=False)
    summary = {
        "cases": int(len(case_df)),
        "baseline_conforming_cases": int(case_df["Conforms_To_Baseline"].sum()),
        "baseline_conformance_percent": round(100 * case_df["Conforms_To_Baseline"].mean(), 2),
        "mean_fitness_vs_baseline_alignment": round(case_df["Fitness_vs_Baseline"].mean(), 4),
        "mean_fitness_vs_discovered_model_token_replay": round(case_df["Fitness_vs_Discovered_Model"].mean(), 4),
        "note": "Synthetic data; baseline is a prototype rule requiring clinical review.",
    }
    (out / "pm4py_conformance_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=Path("careflow_data/clean_event_log.csv"))
    ap.add_argument("--output-dir", type=Path, default=Path("careflow_data/pm4py_conformance"))
    a = ap.parse_args()
    print(json.dumps(run(a.input, a.output_dir), indent=2))
