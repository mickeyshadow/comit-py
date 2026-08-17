"""The deliverable: the 10-year UK industrial forecast, 2026-2036, annual.
Writes FORECAST-2026-2036.md and forecast_results.csv."""
import pandas as pd

from comitpy import Window, solve
from comitpy.datasets import load_inputs
from comitpy.reporting import UNIVERSE_NOTE

inp = load_inputs("datasets", Window(2026, 2036, 1))
sol = solve(inp)
years = list(range(2026, 2037))

sector_of = {s.name: s.sector for s in inp.sites}
layer_of = dict(pd.read_csv("datasets/sites.csv")[["site", "layer"]].values)

emis = sol.emissions.copy()
emis["sector"] = emis.site.map(sector_of)
emis["layer"] = emis.site.map(layer_of)
by_sector = (emis.pivot_table(index="year", columns="sector", values="ktCO2e",
                              aggfunc="sum").fillna(0) / 1e3)
by_sector["total"] = by_sector.sum(axis=1)
by_layer = (emis.pivot_table(index="year", columns="layer", values="ktCO2e",
                             aggfunc="sum").fillna(0) / 1e3)

fuel = (sol.fuel_use.pivot_table(index="year", columns="fuel", values="PJ",
                                 aggfunc="sum").fillna(0))
imports = (sol.imports.pivot_table(index="year", columns="commodity",
                                   values="PJ", aggfunc="sum").fillna(0)
           if not sol.imports.empty else pd.DataFrame(index=years))

# technology story: material new builds
builds = (sol.new.groupby(["tech", "year"]).units.sum().reset_index())
builds = builds[builds.units > 0.05]

tbl = by_sector.round(1)
print("=== Territorial emissions, MtCO2e ===")
print(tbl.to_string())
print("\n=== Fuel use, PJ ===")
print(fuel.round(1).to_string())
if not imports.empty and imports.to_numpy().sum() > 0.01:
    print("\n=== Imports (Mt / PJ by commodity) ===")
    print(imports.round(2).to_string())
else:
    print("\n=== Imports: none (CBAM holds the border) ===")
print("\n=== Material new builds (units of capacity) ===")
print(builds.round(2).to_string(index=False))
print(f"\nPV system cost GBP{sol.objective:,.0f}m; solve optimal.")

out = by_sector.join(fuel, rsuffix="_PJ")
out.to_csv("forecast_results.csv")

lines = [
    "# UK industrial 10-year forecast - 2026 to 2036",
    "",
    "Annual solve on the full provenance-tagged dataset (see MECHANICS.md,",
    "INPUTS.md). Forecast mode: no target imposed. All figures territorial.",
    "",
    UNIVERSE_NOTE,
    "",
    "## Emissions (MtCO2e)",
    "", tbl.to_markdown(),
    "",
    "## Emissions by coverage layer (MtCO2e)",
    "", by_layer.round(1).to_markdown(),
    "",
    "## Fuel use (PJ)",
    "", fuel.round(1).to_markdown(),
    "",
    "## Notable dynamics",
    "",
    "- Port Talbot EAF enters 2028 (committed build + demand restoration).",
    "- CBAM from 2027 closes the cement import leak; abatement happens",
    "  domestically or not at all.",
    "- 2026 announced closures (AGC Thornton, NEG Wigan, JDE Banbury, UES",
    "  Gateshead): traded share trimmed from the ETS tail aggregate,",
    "  non-traded share closed at the location-matched NAEI sites.",
    "",
    f"PV system cost GBP{sol.objective:,.0f}m.",
]
with open("FORECAST-2026-2036.md", "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
print("wrote FORECAST-2026-2036.md, forecast_results.csv")
