"""Site-level fuel use and technology change, with ensemble spreads on the
transition dates (which site converts when is exactly where alternate-optima
uncertainty lives - dates come with their range across worlds, not as
false-precision points).

Writes SITE-DETAIL.md, site_fuel_use.csv, site_technology.csv.
"""
import pandas as pd

from comitpy import Window, solve
from comitpy.datasets import load_inputs
from comitpy.worlds import WORLDS

base = load_inputs("datasets", Window(2026, 2036, 1))
cluster_of = {s.name: s.cluster for s in base.sites}
tech_fuels = {name: t.fuel_use for name, t in base.technologies.items()}

EPS = 1e-3


def site_fuel_use(sol):
    rows = []
    for _, r in sol.used.iterrows():
        for fuel, use in tech_fuels[r.tech].items():
            rows.append((r.site, r.year, fuel, r.units * use))
    return (pd.DataFrame(rows, columns=["site", "year", "fuel", "PJ"])
            .groupby(["site", "year", "fuel"], as_index=False).sum())


def transitions(sol):
    """Per site: technologies arriving (first year used) inside the window."""
    out = []
    for (site, tech), g in sol.used.groupby(["site", "tech"]):
        g = g[g.units > EPS]
        if g.empty:
            continue
        first = int(g.year.min())
        if first > base.window.start:
            out.append((site, tech, first))
    return out


sol = solve(base)
fuel = site_fuel_use(sol)
fuel.round(4).to_csv("site_fuel_use.csv", index=False)
sol.used.round(4).to_csv("site_technology.csv", index=False)

# central transitions
central_tr = transitions(sol)

# transition-date spreads across worlds
arrivals: dict[tuple, list] = {}
for site, tech, year in central_tr:
    arrivals[(site, tech)] = [year]
for name, tf in WORLDS.items():
    for site, tech, year in transitions(solve(tf(base))):
        arrivals.setdefault((site, tech), []).append(year)

tr_rows = []
for (site, tech), years in sorted(arrivals.items()):
    in_central = any(s == site and t == tech for s, t, _ in central_tr)
    tr_rows.append({
        "site": site, "cluster": cluster_of.get(site, "?"), "tech": tech,
        "central_year": (min(y for s, t, y in central_tr
                             if s == site and t == tech)
                         if in_central else None),
        "earliest": min(years), "latest": max(years),
        "n_worlds": len(years),
    })
tr = pd.DataFrame(tr_rows)

# fuel-mix change for the biggest sites
f26 = fuel[fuel.year == 2026].pivot_table(index="site", columns="fuel",
                                          values="PJ").fillna(0)
f36 = fuel[fuel.year == 2036].pivot_table(index="site", columns="fuel",
                                          values="PJ").fillna(0)
big = f26.sum(axis=1).sort_values(ascending=False).head(12).index
mix = pd.concat({"2026": f26.loc[big], "2036": f36.reindex(big).fillna(0)},
                axis=1).round(2)

print("=== Technology arrivals (site, tech, central year, range across worlds) ===")
show = tr.sort_values(["central_year", "site"], na_position="last")
for _, r in show.iterrows():
    cy = int(r.central_year) if pd.notna(r.central_year) else "-"
    tag = "" if r.n_worlds >= 6 else f"  (only {r.n_worlds}/7 worlds)"
    print(f"  {str(r.site)[:40]:40} {r.tech:16} central {cy!s:>5} "
          f"[{int(r.earliest)}-{int(r.latest)}]{tag}")

print("\n=== Fuel mix, top sites, 2026 vs 2036 (PJ) ===")
print(mix.to_string())

lines = ["# Site-level fuel use and technology change", "",
         "Transition dates carry their range across the seven ensemble",
         "worlds; a date appearing in few worlds is a fragile (near-tie)",
         "event, not a forecast.", "",
         "## Technology arrivals", "",
         tr.sort_values(["central_year", "site"], na_position="last")
           .to_markdown(index=False), "",
         "## Fuel mix, largest sites, 2026 vs 2036 (PJ)", "",
         mix.to_markdown()]
with open("SITE-DETAIL.md", "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
print("\nwrote SITE-DETAIL.md, site_fuel_use.csv, site_technology.csv")
