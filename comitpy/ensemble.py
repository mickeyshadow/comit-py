"""Ensemble-first running (item 6): a forecast is a set of worlds, not a
point. Scenarios are named transforms of Inputs; results come back tidy for
fan charts and range statements."""
from __future__ import annotations

from typing import Callable

import pandas as pd

from .inputs import Inputs
from .model import Solution, solve


def run_ensemble(base: Inputs,
                 scenarios: dict[str, Callable[[Inputs], Inputs]]
                 ) -> tuple[dict[str, Solution], pd.DataFrame]:
    """Solve the base plus every scenario transform. Returns solutions and a
    tidy fuel-use comparison (scenario, fuel, year, PJ)."""
    sols = {"central": solve(base)}
    for name, transform in scenarios.items():
        sols[name] = solve(transform(base))
    rows = []
    for name, sol in sols.items():
        for _, r in sol.fuel_use.iterrows():
            rows.append((name, r.fuel, r.year, r.PJ))
        for _, r in sol.imports.iterrows():
            rows.append((name, f"import:{r.commodity}", r.year, r.PJ))
    tidy = pd.DataFrame(rows, columns=["scenario", "fuel", "year", "PJ"])
    return sols, tidy


def spread(tidy: pd.DataFrame, fuel: str, year: int) -> tuple[float, float]:
    """Min/max across the ensemble — the honest quotable range."""
    sel = tidy[(tidy.fuel == fuel) & (tidy.year == year)]
    if sel.empty:
        return (0.0, 0.0)
    return (float(sel.PJ.min()), float(sel.PJ.max()))
