"""The deliverable run: a 10-year annual forecast (2026-2036) of UK industry
on real, provenance-tagged data - plus a net-zero pathway variant to show
the same model answering the pathway question.
"""
import pandas as pd

from comitpy import BuildOrder, ImportOption, Window, pins, solve
from comitpy.datasets import load_inputs
from comitpy.pathways import netzero_2050

# ---- 10-year forecast mode --------------------------------------------------
inp = load_inputs("datasets", Window(2026, 2036, 1))

# committed real-world facts (v0: in code, sources as comments; move to
# datasets/build_orders.csv as the list grows)
inp = inp.with_(
    build_orders=[
        # Tata Port Talbot EAF: FID taken, construction Jul 2025, ops end-2027
        BuildOrder("Port Talbot Steelworks", "eaf", 2028, min_units=3.0),
    ],
    imports=[
        # the import/closure margin: delivered import parity prices
        ImportOption("steel", pins({2026: 520.0})),    # ~GBP520/t delivered
        ImportOption("cement", pins({2026: 100.0})),   # ~GBP100/t delivered
        ImportOption("heat", pins({2026: 10_000.0})),  # heat does not import
    ])

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
