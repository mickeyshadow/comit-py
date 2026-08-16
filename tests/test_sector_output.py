"""Sector output indices must scale site demand curves."""
import pytest

from comitpy import Window
from comitpy.datasets import load_inputs


def test_indices_scale_demand():
    inp = load_inputs("datasets_backcast", Window(2021, 2029, 1))
    steel = next(s for s in inp.sites if s.sector == "steel")
    base = steel.demand["steel"](2021)
    assert steel.demand["steel"](2023) == pytest.approx(base * 0.78, rel=1e-6)
    heat = next(s for s in inp.sites if s.sector == "heat")
    hbase = heat.demand["heat"](2021)
    assert heat.demand["heat"](2022) == pytest.approx(hbase * 0.96, rel=1e-6)
