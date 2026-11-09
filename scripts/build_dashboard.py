#!/usr/bin/env python3
"""Build the self-contained CareFlow process-mining dashboard (HTML, no server needed).

Reads the clean event log, embeds case-level data, and writes dashboard/careflow_dashboard.html.
Filters (age band, arrival shift, physician) re-compute the process map, KPIs and bottlenecks in-browser.
All data is synthetic.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

BASELINE = ["Registration", "Triage", "Physician Assessment", "X-Ray",
            "Physician Reassessment", "Treatment", "Discharge"]


def build_cases(path: Path) -> list[dict]:
    ev = pd.read_csv(path, parse_dates=["Timestamp"]).sort_values(["Case_ID", "Timestamp"], kind="stable")
    out = []
    for cid, g in ev.groupby("Case_ID", sort=True):
        acts, ts = g["Activity_Name"].tolist(), g["Timestamp"].tolist()
        doc = g.loc[g["Activity_Name"] == "Physician Assessment", "Resource_ID"]
        tr = [[acts[i], acts[i + 1], round((ts[i + 1] - ts[i]).total_seconds() / 60, 1)] for i in range(len(acts) - 1)]
        out.append({"id": cid, "age": g["Age_Band"].iloc[0], "shift": g["Arrival_Shift"].iloc[0].split(" (")[0],
                    "doc": doc.iloc[0] if len(doc) else "n/a",
                    "dur": round((ts[-1] - ts[0]).total_seconds() / 60, 1),
                    "conf": acts == BASELINE, "loop": any(t[0] == "X-Ray" and t[1] == "Triage" for t in tr), "tr": tr})
    return out


TEMPLATE = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>CareFlow — Clinical Pathway Dashboard</title>
<style>
:root{--bg:#f6f8fb;--card:#fff;--tx:#1b2430;--mut:#667085;--bd:#e3e8ef;--ac:#0b6e99;--bad:#c62828;--ok:#2e7d32}
@media(prefers-color-scheme:dark){:root{--bg:#0f1720;--card:#18222e;--tx:#e8eef5;--mut:#9aa8b8;--bd:#2a3746;--ac:#4fb3e0;--bad:#ff6b6b;--ok:#6fcf7a}}
*{box-sizing:border-box}body{margin:0;font:14px system-ui,sans-serif;background:var(--bg);color:var(--tx)}
header{padding:16px 24px;border-bottom:1px solid var(--bd);background:var(--card)}h1{margin:0;font-size:20px}
header p{margin:4px 0 0;color:var(--mut);font-size:12px}main{padding:16px 24px;max-width:1200px;margin:auto}
.filters{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px}label{font-size:12px;color:var(--mut);display:flex;flex-direction:column;gap:3px}
select{padding:6px 8px;border:1px solid var(--bd);border-radius:6px;background:var(--card);color:var(--tx)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin-bottom:14px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:12px 14px}
.kpi b{display:block;font-size:24px;margin-top:2px}.kpi span{font-size:12px;color:var(--mut)}
.grid{display:grid;grid-template-columns:3fr 2fr;gap:12px}@media(max-width:850px){.grid{grid-template-columns:1fr}}
h2{font-size:14px;margin:0 0 8px}table{width:100%;border-collapse:collapse;font-size:12px}
th,td{text-align:left;padding:5px 4px;border-bottom:1px solid var(--bd)}td.n{text-align:right}
.scroll{overflow-x:auto}.note{font-size:11px;color:var(--mut);margin-top:12px}.bar{height:8px;background:var(--bad);border-radius:4px}
svg text{fill:var(--tx);font-size:11px}
</style></head><body>
<header><h1>CareFlow — Clinical Pathway Process Mining</h1>
<p>Synthetic EHR event log · illustrative results only, not real hospital performance</p></header>
<main>
<div class="filters">
<label>Age band<select id="fAge"></select></label><label>Arrival shift<select id="fShift"></select></label>
<label>Physician (assessment)<select id="fDoc"></select></label></div>
<div class="kpis" id="kpis"></div>
<div class="grid">
<div class="card"><h2>Process map (spaghetti view) — edge width = patient count, red = longer mean gap</h2>
<div class="scroll"><svg id="map" viewBox="0 0 760 360" width="100%" role="img" aria-label="Process map"></svg></div></div>
<div class="card"><h2>Bottlenecks: mean minutes between events</h2><div class="scroll"><table id="bt"></table></div></div></div>
<div class="grid" style="margin-top:12px">
<div class="card"><h2>Process variants</h2><div class="scroll"><table id="var"></table></div></div>
<div class="card"><h2>What-if: remove the X-Ray → Triage loop</h2><div id="whatif"></div></div></div>
<p class="note">Elapsed time = gap between consecutive recorded events (not pure waiting time). Baseline conformance = exact match to
Registration → Triage → Physician Assessment → X-Ray → Physician Reassessment → Treatment → Discharge (prototype rule).
The what-if compares looped vs. non-looped cases in this synthetic data; it is a scenario estimate, not evidence of real-world improvement.</p>
</main>
<script>
const CASES=__DATA__;
const POS={"Registration":[70,60],"Triage":[230,60],"Physician Assessment":[400,60],"X-Ray":[570,60],"Paperwork Completion":[400,200],
"Physician Reassessment":[570,200],"Treatment":[570,310],"Discharge":[250,310]};
const $=id=>document.getElementById(id);
const uniq=k=>["All",...[...new Set(CASES.map(c=>c[k]))].sort()];
[["fAge","age"],["fShift","shift"],["fDoc","doc"]].forEach(([id,k])=>{$(id).innerHTML=uniq(k).map(v=>`<option>${v}</option>`).join("");$(id).onchange=render});
const mean=a=>a.length?a.reduce((x,y)=>x+y,0)/a.length:0, f1=x=>x.toFixed(1);
function render(){
 const a=$("fAge").value,s=$("fShift").value,d=$("fDoc").value;
 const cs=CASES.filter(c=>(a=="All"||c.age==a)&&(s=="All"||c.shift==s)&&(d=="All"||c.doc==d));
 const n=cs.length,loops=cs.filter(c=>c.loop),clean=cs.filter(c=>!c.loop);
 const kp=[["Cases",n],["Mean case time (min)",f1(mean(cs.map(c=>c.dur)))],["X-Ray → Triage loopback",n?f1(100*loops.length/n)+"%":"–"],
  ["Baseline conformance",n?f1(100*cs.filter(c=>c.conf).length/n)+"%":"–"]];
 $("kpis").innerHTML=kp.map(k=>`<div class="card kpi"><span>${k[0]}</span><b>${k[1]}</b></div>`).join("");
 const E={};cs.forEach(c=>c.tr.forEach(t=>{const k=t[0]+"|"+t[1];(E[k]=E[k]||[]).push(t[2])}));
 const rows=Object.entries(E).map(([k,v])=>{const[p,q]=k.split("|");return{p,q,n:v.length,m:mean(v)}}).sort((x,y)=>y.m-x.m);
 const mx=Math.max(1,...rows.map(r=>r.n)),mm=Math.max(1,...rows.map(r=>r.m));
 let svg=`<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0L10,5L0,10z" fill="#888"/></marker></defs>`;
 rows.forEach(r=>{const A=POS[r.p],B=POS[r.q];if(!A||!B)return;const w=1+7*r.n/mx,red=Math.round(255*r.m/mm);
  const bend=(r.p=="X-Ray"&&r.q=="Triage")?-70:0,mx_=(A[0]+B[0])/2,my=(A[1]+B[1])/2+bend;
  svg+=`<path d="M${A[0]},${A[1]} Q${mx_},${my} ${B[0]},${B[1]}" fill="none" stroke="rgb(${60+red*0.75|0},${110-red*0.3|0},${140-red*0.4|0})" stroke-width="${w}" opacity=".75" marker-end="url(#ar)"/>
  <text x="${mx_}" y="${my-4}" text-anchor="middle">${r.n} · ${f1(r.m)}m</text>`});
 Object.entries(POS).forEach(([k,[x,y]])=>{svg+=`<rect x="${x-52}" y="${y-15}" width="104" height="30" rx="8" fill="var(--card)" stroke="var(--ac)" stroke-width="1.5"/><text x="${x}" y="${y+4}" text-anchor="middle">${k.replace("Physician","Phys.")}</text>`});
 $("map").innerHTML=svg;
 $("bt").innerHTML="<tr><th>Transition</th><th>Cases</th><th>Mean min</th><th></th></tr>"+rows.map(r=>`<tr><td>${r.p} → ${r.q}</td><td class="n">${r.n}</td><td class="n">${f1(r.m)}</td><td style="width:70px"><div class="bar" style="width:${100*r.m/mm}%"></div></td></tr>`).join("");
 const V={};cs.forEach(c=>{const k=[c.tr[0][0],...c.tr.map(t=>t[1])].join(" → ");(V[k]=V[k]||[]).push(c.dur)});
 $("var").innerHTML="<tr><th>Variant</th><th>Cases</th><th>Share</th><th>Mean min</th></tr>"+Object.entries(V).sort((x,y)=>y[1].length-x[1].length).map(([k,v])=>`<tr><td>${k}</td><td class="n">${v.length}</td><td class="n">${f1(100*v.length/n)}%</td><td class="n">${f1(mean(v))}</td></tr>`).join("");
 const ml=mean(loops.map(c=>c.dur)),mc=mean(clean.map(c=>c.dur)),gap=loops.length&&clean.length?ml-mc:0,save=n?gap*loops.length/n:0;
 $("whatif").innerHTML=n?`<p>Looped cases average <b>${f1(ml)}</b> min vs <b>${f1(mc)}</b> min without the loop (gap ${f1(gap)} min).</p>
 <p>If the intake paperwork gap were fixed and the loop eliminated, the average case time in this selection would fall by about <b>${f1(save)} min</b> (${f1(100*save/mean(cs.map(c=>c.dur)))}%).</p>`:"No cases match the filters.";
}
render();
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=Path("careflow_data/clean_event_log.csv"))
    ap.add_argument("--output", type=Path, default=Path("dashboard/careflow_dashboard.html"))
    a = ap.parse_args()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(TEMPLATE.replace("__DATA__", json.dumps(build_cases(a.input), separators=(",", ":"))), encoding="utf-8")
    print(f"Dashboard written to {a.output}")


if __name__ == "__main__":
    main()
