"""Calibrate usage_inertia_cost against the backcast's 2022 dip.

Target: the model held gas through the 2022 price spike no better than
index 85.7 vs reality's 95.8. Sweep the disruption cost; adopt where the
dip matches, watching total MAPE and the same misattribution trap as the
hurdle calibration (don't tune inertia to impersonate the closure margin).
"""
import pandas as pd

from comitpy import ImportOption, Window, pins, solve
from comitpy.datasets import load_inputs
from comitpy.skill import indexed_mape

base = load_inputs("datasets_backcast", Window(2021, 2029, 1)).with_(
    imports=[ImportOption("steel", pins({2021: 500.0})),
             ImportOption("cement", pins({2021: 90.0}))])
outturn = pd.read_csv("datasets_backcast/outturn.csv")[["year", "value"]]

print("inertia GBPm/PJ | 2022 2023 2024 2025 (idx) | MAPE")
for cost in [0, 24, 36, 48, 72]:
    sol = solve(base.with_(usage_inertia_cost=float(cost)))
    modelled = (sol.emissions.groupby("year").ktCO2e.sum()
                .loc[2021:2025].reset_index()
                .rename(columns={"ktCO2e": "value"}))
    mape, tbl = indexed_mape(modelled, outturn, 2021)
    idx = tbl[tbl.year > 2021].modelled_idx.round(1).tolist()
    print(f"{cost:>14} | {idx} | {100*mape:.1f}%  "
          f"(outturn: {tbl[tbl.year > 2021].outturn_idx.round(1).tolist()})")
