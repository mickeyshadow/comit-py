"""Rolling-horizon (myopic) mode (item 7): solve a short window, fix what was
built, roll forward. The gap between this and the perfect-foresight solve
measures how much a forecast depends on firms seeing the future."""
from __future__ import annotations

import pandas as pd
from dataclasses import replace

from .inputs import Inputs, Site, Window
from .model import Solution, solve


def rolling_solve(inputs: Inputs, window_width: int) -> pd.DataFrame:
    """Returns combined used-capacity records across all rolled windows
    (first window-step of each solve is kept, capacity carries forward)."""
    years = inputs.window.years
    dt = inputs.window.timestep
    carried: dict[str, dict[str, float]] = {
        s.name: dict(s.start_capacity) for s in inputs.sites}
    kept = []

    step = 0
    while step < len(years):
        w_start = years[step]
        w_end = min(w_start + window_width - 1, inputs.window.end)
        sites = [replace(s, start_capacity=dict(carried[s.name]))
                 for s in inputs.sites]
        sub = replace(inputs, window=Window(w_start, w_end, dt), sites=sites)
        sol = solve(sub)

        keep_years = {w_start}
        kept.append(sol.used[sol.used.year.isin(keep_years)])
        built = sol.new[sol.new.year.isin(keep_years)]
        for _, r in built.iterrows():
            carried[r.site][r.tech] = carried[r.site].get(r.tech, 0.0) + r.units
        step += 1

    return pd.concat(kept, ignore_index=True) if kept else pd.DataFrame()
