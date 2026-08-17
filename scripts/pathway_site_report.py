"""Site-level detail for the net-zero pathway: what the cap FORCES that
economics alone would not, site by site, with dates - compared like-for-like
against forecast mode on the same 2026-2050 window.

Pathway dates also carry ensemble ranges (worlds applied under the same cap,
which is held fixed from the central base year for comparability).

Writes PATHWAY-SITE-DETAIL.md, pathway_site_technology.csv,
pathway_site_fuel_use.csv.
"""
import pandas as pd

from comitpy import Window, solve
from comitpy.datasets import load_inputs
from comitpy.pathways import netzero_2050
from comitpy.reporting import UNIVERSE_NOTE, site_fuel_use, transitions
from comitpy.worlds import WORLDS

W = Window(2026, 2050, 2)
base = load_inputs("datasets", W)
cluster_of = {s.name: s.cluster for s in base.sites}

fc = solve(base)
base_emis = float(fc.emissions.query("year == 2026").ktCO2e.sum())
pathway = netzero_2050(base_emis, start=2026)
pw = solve(pathway(base))

fc_tr = {(s, t): y for s, t, y in transitions(fc, W.start)}
pw_tr = {(s, t): y for s, t, y in transitions(pw, W.start)}

# ensemble ranges on pathway dates (same cap in every world)
arrivals: dict[tuple, list] = {k: [y] for k, y in pw_tr.items()}
for name, tf in WORLDS.items():
    for s, t, y in transitions(solve(pathway(tf(base))), W.start):
        arrivals.setdefault((s, t), []).append(y)

rows = []
for (site, tech), years in sorted(arrivals.items()):
    in_fc = (site, tech) in fc_tr
    rows.append({
        "site": site, "cluster": cluster_of.get(site, "?"), "tech": tech,
        "pathway_year": pw_tr.get((site, tech)),
        "earliest": min(years), "latest": max(years),
        "n_worlds": len(years),
        "forecast_year": fc_tr.get((site, tech)),
        "cap_forced": "yes" if not in_fc else
                      ("earlier" if pw_tr.get((site, tech), 9999)
                       < fc_tr[(site, tech)] else ""),
    })
tr = pd.DataFrame(rows)

forced = tr[tr.cap_forced == "yes"]
pd.set_option("display.width", 140)
print(f"Forecast-mode arrivals: {len(fc_tr)}; pathway arrivals: {len(pw_tr)}; "
      f"cap-forced (absent from forecast): {len(forced)}\n")
print("=== Cap-forced technology arrivals (not in the economic forecast) ===")
show = forced.sort_values(["pathway_year", "site"])
for _, r in show.head(30).iterrows():
    tag = "" if r.n_worlds >= 6 else f"  (only {r.n_worlds}/7 worlds)"
    print(f"  {str(r.site)[:40]:40} {r.tech:16} "
          f"{int(r.pathway_year)} [{int(r.earliest)}-{int(r.latest)}]{tag}")
if len(show) > 30:
    print(f"  ... and {len(show) - 30} more (see CSV)")

# fuel mix: pathway vs forecast at 2050, national
f_fc = site_fuel_use(fc, base.technologies)
f_pw = site_fuel_use(pw, base.technologies)
nat = pd.concat({
    "forecast_2050": f_fc.query("year == 2050").groupby("fuel").PJ.sum(),
    "pathway_2050": f_pw.query("year == 2050").groupby("fuel").PJ.sum(),
}, axis=1).fillna(0).round(1)
print("\n=== National fuel mix at 2050: forecast vs net-zero pathway (PJ) ===")
print(nat.to_string())

emis_cmp = pd.concat({
    "forecast": fc.emissions.groupby("year").ktCO2e.sum() / 1e3,
    "pathway": pw.emissions.groupby("year").ktCO2e.sum() / 1e3,
}, axis=1).round(1)
print("\n=== Emissions (MtCO2e) ===")
print(emis_cmp.loc[[2026, 2030, 2036, 2042, 2050]].to_string())

tr.to_csv("pathway_site_technology.csv", index=False)
f_pw.round(4).to_csv("pathway_site_fuel_use.csv", index=False)

lines = [
    "# Site detail under the net-zero-2050 pathway",
    "",
    UNIVERSE_NOTE,
    "",
    "Like-for-like against forecast mode on 2026-2050. 'cap_forced = yes'",
    "marks arrivals the economics alone never produce - the pathway's real",
    "content. Dates carry ranges across the seven worlds under the same cap;",
    "few-world events are fragile near-ties, not forecasts.",
    "",
    "## Emissions", "", emis_cmp.loc[[2026, 2030, 2036, 2042, 2050]].to_markdown(),
    "",
    "## National fuel mix at 2050", "", nat.to_markdown(),
    "",
    "## All pathway arrivals", "",
    tr.sort_values(["pathway_year", "site"]).to_markdown(index=False),
]
with open("PATHWAY-SITE-DETAIL.md", "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
print("\nwrote PATHWAY-SITE-DETAIL.md + CSVs")
