"""The deliverable run: a 10-year annual forecast (2026-2036) of UK industry
on real, provenance-tagged data - plus a net-zero pathway variant to show
the same model answering the pathway question.
"""
import pandas as pd

from comitpy import Window, solve
from comitpy.datasets import load_inputs
from comitpy.pathways import netzero_2050

# ---- 10-year forecast mode --------------------------------------------------
# Every driver lives in datasets/ - this file only chooses the window and
# reports. Imports (with CBAM), build orders, closures, overrides, prices:
# all CSVs, all provenance-tagged.
inp = load_inputs("datasets", Window(2026, 2036, 1))

sol = solve(inp)
print(f"FORECAST 2026-2036: optimal, PV cost GBP{sol.objective:,.0f}m")
emis = sol.emissions.groupby("year").ktCO2e.sum()
print("territorial emissions (MtCO2e):",
      {int(y): round(v / 1e3, 1) for y, v in emis.items() if y % 2 == 0})
imports = sol.imports.groupby(["commodity", "year"]).PJ.sum()
print("imports by 2036:",
      {c: round(v, 2) for (c, y), v in imports.items() if y == 2036})
fuels = sol.fuel_use[sol.fuel_use.year == 2036].set_index("fuel").PJ
print("2036 fuel mix (PJ):", {f: round(v, 1) for f, v in fuels.items()})
sol.emissions.to_csv("results_forecast_emissions.csv", index=False)

# ---- pathway mode -----------------------------------------------------------
base_2026 = float(emis.iloc[0])
pw = netzero_2050(base_2026, start=2026)(
    inp.with_(window=Window(2026, 2050, 2)))
psol = solve(pw)
pemis = psol.emissions.groupby("year").ktCO2e.sum()
print(f"\nPATHWAY net-zero-2050: optimal, PV cost GBP{psol.objective:,.0f}m")
print("cap-bound emissions (MtCO2e):",
      {int(y): round(v / 1e3, 1) for y, v in pemis.items() if y % 6 == 2})
