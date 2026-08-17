"""The forecast as ranges: seven named worlds, one lever each.

Writes ENSEMBLE-FORECAST.md and ensemble_results.csv."""
import pandas as pd

from comitpy import Window, solve
from comitpy.datasets import load_inputs
from comitpy.reporting import UNIVERSE_NOTE
from comitpy.worlds import (WORLDS, scale_carbon,
                            scale_fuel, slip_ccs)

base = load_inputs("datasets", Window(2026, 2036, 1))









rows = []
sols = {"central": solve(base)}
for name, tf in WORLDS.items():
    sols[name] = solve(tf(base))

for name, sol in sols.items():
    e = sol.emissions.groupby("year").ktCO2e.sum() / 1e3
    f = sol.fuel_use.pivot_table(index="year", columns="fuel", values="PJ",
                                 aggfunc="sum").fillna(0)
    for y in range(2026, 2037):
        rows.append({
            "scenario": name, "year": y,
            "MtCO2e": round(float(e.get(y, 0)), 2),
            "gas_PJ": round(float(f.gas.get(y, 0)) if "gas" in f else 0, 1),
            "elec_PJ": round(float(f.electricity.get(y, 0))
                             if "electricity" in f else 0, 1),
        })
tidy = pd.DataFrame(rows)
tidy.to_csv("ensemble_results.csv", index=False)

emis = tidy.pivot_table(index="year", columns="scenario", values="MtCO2e")
order = ["central"] + list(WORLDS)
emis = emis[order]
lo = emis.min(axis=1)
hi = emis.max(axis=1)

print("=== Territorial emissions by world (MtCO2e) ===")
print(emis.round(1).to_string())
print("\n=== The range ===")
for y in (2028, 2030, 2033, 2036):
    print(f"  {y}: {lo[y]:.1f} - {hi[y]:.1f} Mt "
          f"(central {emis.loc[y, 'central']:.1f})")

e36 = tidy[tidy.year == 2036].set_index("scenario")
print("\n=== 2036 snapshot by world ===")
print(e36[["MtCO2e", "gas_PJ", "elec_PJ"]].loc[order].to_string())

lines = ["# The forecast as ranges - seven worlds, one lever each", "", UNIVERSE_NOTE, "",
         "Central plus six single-lever variants (levies rebalancing, gas",
         "+50%/-30%, carbon x1.5/x0.6, CCS slipping 4 years at half ramp).",
         "", "## Emissions (MtCO2e)", "", emis.round(1).to_markdown(), "",
         "## 2036 snapshot", "",
         e36[["MtCO2e", "gas_PJ", "elec_PJ"]].loc[order].to_markdown()]
with open("ENSEMBLE-FORECAST.md", "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
print("\nwrote ENSEMBLE-FORECAST.md, ensemble_results.csv")
