"""The provenance layer and the real-data forecast must both hold."""
import pandas as pd
import pytest

from comitpy import Window, solve
from comitpy.datasets import load_inputs
from comitpy.pathways import netzero_2050

DATA = "datasets"


def test_datasets_load_and_forecast_solves():
    inp = load_inputs(DATA, Window(2026, 2036, 2))
    sol = solve(inp)
    assert sol.status == "optimal"
    assert not sol.emissions.empty


def test_provenance_is_enforced(tmp_path):
    import shutil
    shutil.copytree(DATA, tmp_path / "d", dirs_exist_ok=True)
    carbon = pd.read_csv(tmp_path / "d" / "carbon.csv")
    carbon.loc[0, "basis"] = "trust_me"
    carbon.to_csv(tmp_path / "d" / "carbon.csv", index=False)
    with pytest.raises(ValueError, match="provenance"):
        load_inputs(str(tmp_path / "d"), Window(2026, 2036, 2))


def test_pathway_cap_binds():
    inp = load_inputs(DATA, Window(2026, 2046, 4))
    free = solve(inp)
    base = float(free.emissions.query("year == 2026").ktCO2e.sum())
    capped = solve(netzero_2050(base, start=2026)(inp))
    for y in sorted(set(capped.emissions.year)):
        # linear decline to the 5% residual by 2050
        frac = min(1.0, (y - 2026) / (2050 - 2026))
        cap = base * (1 - 0.95 * frac)
        tot = capped.emissions.query("year == @y").ktCO2e.sum()
        assert tot <= cap + 1e-6
    late_free = free.emissions.query("year == 2046").ktCO2e.sum()
    late_capped = capped.emissions.query("year == 2046").ktCO2e.sum()
    assert late_capped < late_free
