"""Solve the standard run set and write results_store.csv - the one table
the dashboard reads. Runs:

- central + the six ensemble worlds, 2026-2036 annual (the forecast set)
- forecast_2050 + netzero_2050, 2026-2050 biennial (the pathway pair,
  central lever settings; pathway worlds live in the report scripts)
"""
import pandas as pd

from comitpy import Window, solve
from comitpy.datasets import load_inputs
from comitpy.pathways import netzero_2050
from comitpy.results_store import solution_frame
from comitpy.worlds import WORLDS

layer_of = dict(pd.read_csv("datasets/sites.csv")[["site", "layer"]].values)

frames = []

base = load_inputs("datasets", Window(2026, 2036, 1))
for run, transform in [("central", lambda i: i)] + list(WORLDS.items()):
    sol = solve(transform(base))
    frames.append(solution_frame(run, base, sol, layer_of))
    print(f"{run}: objective GBP{sol.objective:,.0f}m")

long = load_inputs("datasets", Window(2026, 2050, 2))
fc = solve(long)
frames.append(solution_frame("forecast_2050", long, fc, layer_of))
base_emis = float(fc.emissions.query("year == 2026").ktCO2e.sum())
pw = solve(netzero_2050(base_emis, start=2026)(long))
frames.append(solution_frame("netzero_2050", long, pw, layer_of))
print(f"pathway pair: forecast GBP{fc.objective:,.0f}m / "
      f"netzero GBP{pw.objective:,.0f}m")

store = pd.concat(frames, ignore_index=True)
store.to_csv("results_store.csv", index=False)
print(f"wrote results_store.csv: {len(store):,} rows, "
      f"{store.run.nunique()} runs")
