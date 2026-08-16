"""The skill gate: stand in 2021 on historical inputs, solve annually,
score 2021-2025 indexed trajectories against UK ETS outturn on the
identical site universe. Reference points from the R-model harness
(comit-harness BACKCAST-SKILL.md): outturn index fell 95.8 / 90.3 / 80.6 /
67.7 (2022-2025); the calibrated R fork tracked ~flat (its missing closure
margin); dummy-price R over-decarbonised wildly.
"""
import pandas as pd

from comitpy import Window, solve
from comitpy.datasets import load_inputs
from comitpy.skill import indexed_mape

inp = load_inputs("datasets_backcast", Window(2021, 2029, 1))

sol = solve(inp)
modelled = (sol.emissions.groupby("year").ktCO2e.sum()
            .loc[2021:2025].reset_index()
            .rename(columns={"ktCO2e": "value"}))
outturn = pd.read_csv("datasets_backcast/outturn.csv")[["year", "value"]]

mape, tbl = indexed_mape(modelled, outturn, 2021)
print("Backcast 2021-2025, indexed to 2021=100:")
print(tbl.round(1).to_string(index=False))
print(f"\n**Indexed-trajectory MAPE 2022-2025: {100*mape:.1f}%**")
print("R-model references (harness): calibrated fork ~flat-100 profile "
      "(MAPE ~24-28% equivalent basis); outturn driven by closures/output cuts.")

imports = sol.imports.groupby(["commodity", "year"]).PJ.sum()
print("\nimports (Mt) in scored years:",
      {(c, int(y)): round(v, 2) for (c, y), v in imports.items() if y <= 2025})

lvl = modelled.merge(outturn, on="year", suffixes=("_model", "_outturn"))
lvl["ratio"] = lvl.value_model / lvl.value_outturn
print("\nlevel ratio model/outturn (boundary+derivation offset, not skill):",
      [round(r, 2) for r in lvl.ratio])
