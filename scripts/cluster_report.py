"""Split the 10-year forecast to cluster and site level, with confidence
stated per level:

- CLUSTER: robust. Aggregation washes out the alternate-optima noise the
  harness documented; cluster totals were stable under every degeneracy
  probe.
- SITE: meaningful where a committed event or a dominant economic gradient
  pins it (Port Talbot, the CCS build-out sites); indicative elsewhere -
  quote ranges from the ensemble, not points.

Writes CLUSTER-FORECAST.md, cluster_results.csv, site_results.csv.
"""
import dataclasses

import pandas as pd

from comitpy import Window, solve
from comitpy.datasets import load_inputs
from comitpy.inputs import Fuel, PriceStack

base = load_inputs("datasets", Window(2026, 2036, 1))
cluster_of = {s.name: s.cluster for s in base.sites}
sector_of = {s.name: s.sector for s in base.sites}


def with_cluster(df):
    df = df.copy()
    df["cluster"] = df.site.map(cluster_of)
    df["sector"] = df.site.map(sector_of)
    return df


# ---- central, by cluster ----------------------------------------------------
sol = solve(base)
emis = with_cluster(sol.emissions)
by_cluster = (emis.pivot_table(index="year", columns="cluster",
                               values="ktCO2e", aggfunc="sum").fillna(0) / 1e3)
by_cluster = by_cluster[sorted(by_cluster.columns,
                               key=lambda c: -by_cluster[c].iloc[0])]

# ---- ensemble ranges per cluster at 2036 (same 6 worlds as the ensemble) ----
def scale_fuel(inp, fuel, component, factor):
    f = inp.fuels[fuel]
    st = f.stack
    parts = {c: getattr(st, c) for c in ("wholesale", "network", "levies",
                                         "margin")}
    old = parts[component]
    parts[component] = (lambda y, _o=old: _o(y) * factor)
    fuels = dict(inp.fuels)
    fuels[fuel] = Fuel(f.name, PriceStack(parts["wholesale"], parts["network"],
                                          parts["levies"], parts["margin"],
                                          st.band_factors),
                       f.emissions_ktco2e_per_pj)
    return inp.with_(fuels=fuels)


def scale_carbon(inp, factor):
    c = inp.carbon_price_traded
    return inp.with_(carbon_price_traded=lambda y, _c=c: _c(y) * factor)


def slip_ccs(inp):
    techs = dict(inp.technologies)
    for name in ("cement_kiln_ccs", "gas_boiler_ccs"):
        t = techs[name]
        techs[name] = dataclasses.replace(
            t, first_year=t.first_year + 4,
            ramp_limit=(t.ramp_limit or 0) * 0.5 or None)
    return inp.with_(technologies=techs)


WORLDS = {
    "levies_off": lambda i: scale_fuel(i, "electricity", "levies", 0.0),
    "gas_up50": lambda i: scale_fuel(i, "gas", "wholesale", 1.5),
    "gas_down30": lambda i: scale_fuel(i, "gas", "wholesale", 0.7),
    "carbon_x1.5": lambda i: scale_carbon(i, 1.5),
    "carbon_x0.6": lambda i: scale_carbon(i, 0.6),
    "ccs_slip": slip_ccs,
}

c36 = {"central": emis.query("year == 2036").groupby("cluster").ktCO2e.sum() / 1e3}
site36 = {"central": emis.query("year == 2036").set_index("site").ktCO2e / 1e3}
for name, tf in WORLDS.items():
    s = with_cluster(solve(tf(base)).emissions)
    c36[name] = s.query("year == 2036").groupby("cluster").ktCO2e.sum() / 1e3
    site36[name] = s.query("year == 2036").set_index("site").ktCO2e / 1e3

cr = pd.DataFrame(c36).fillna(0)
cr["lo"], cr["hi"] = cr.min(axis=1), cr.max(axis=1)
cr = cr.sort_values("central", ascending=False)

sr = pd.DataFrame(site36).fillna(0)
sr["lo"], sr["hi"] = sr.min(axis=1), sr.max(axis=1)
sr["cluster"] = [cluster_of.get(s, "?") for s in sr.index]
sr["sector"] = [sector_of.get(s, "?") for s in sr.index]
top_sites = sr.sort_values("central", ascending=False).head(20)

print("=== Central forecast by cluster (MtCO2e) ===")
print(by_cluster.round(2).to_string())
print("\n=== 2036 by cluster: central and ensemble range (MtCO2e) ===")
print(cr[["central", "lo", "hi"]].round(2).to_string())
print("\n=== Top 20 sites at 2036: central [lo-hi] (MtCO2e) ===")
for s, r in top_sites.iterrows():
    print(f"  {s[:42]:42} {r.cluster:12} {r.sector:7} "
          f"{r.central:6.2f}  [{r.lo:.2f}-{r.hi:.2f}]")

by_cluster.round(3).to_csv("cluster_results.csv")
sr.round(3).to_csv("site_results.csv")

lines = [
    "# The forecast split by cluster and site",
    "",
    "Confidence differs by level, per the degeneracy analysis: cluster",
    "totals are robust (aggregation), site figures are pinned where a",
    "committed event or dominant gradient holds them and indicative",
    "elsewhere - the ensemble range travels with every number.",
    "",
    "## Central forecast by cluster (MtCO2e)",
    "", by_cluster.round(2).to_markdown(),
    "",
    "## 2036 by cluster with ensemble range",
    "", cr[["central", "lo", "hi"]].round(2).to_markdown(),
    "",
    "## Top 20 sites at 2036 (central [lo-hi])",
    "", top_sites[["cluster", "sector", "central", "lo", "hi"]]
        .round(2).to_markdown(),
]
with open("CLUSTER-FORECAST.md", "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
print("\nwrote CLUSTER-FORECAST.md, cluster_results.csv, site_results.csv")
