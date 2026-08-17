"""The results store is the dashboard's only input - pin that it carries
everything the solution does, with metadata on every row."""
import pandas as pd
import pytest

from comitpy import Window, solve
from comitpy.datasets import load_inputs
from comitpy.results_store import COLUMNS, solution_frame


@pytest.fixture(scope="module")
def frame():
    inp = load_inputs("datasets", Window(2026, 2030, 2))
    sol = solve(inp)
    layer_of = dict(pd.read_csv("datasets/sites.csv")[["site", "layer"]].values)
    return inp, sol, solution_frame("central", inp, sol, layer_of)


def test_schema_and_metadata_complete(frame):
    _, _, df = frame
    assert list(df.columns) == COLUMNS
    # denormalised metadata must exist on every row - a blank layer or
    # cluster silently drops the row from every dashboard filter
    for col in ("run", "site", "sector", "layer", "cluster", "variable"):
        assert not df[col].isna().any(), col
        assert (df[col] != "").all(), col


def test_totals_match_solution(frame):
    inp, sol, df = frame
    emis = df[df.variable == "emissions_ktco2e"].value.sum()
    assert emis == pytest.approx(sol.emissions.ktCO2e.sum())
    fuel = (df[df.variable == "fuel_use_pj"]
            .groupby("detail").value.sum())
    for _, r in sol.fuel_use.groupby("fuel").PJ.sum().reset_index().iterrows():
        assert fuel[r.fuel] == pytest.approx(r.PJ), r.fuel
