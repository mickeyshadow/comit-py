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


def test_forward_indices_and_overrides():
    inp = load_inputs("datasets", Window(2026, 2036, 1))
    cem = next(s for s in inp.sites if s.sector == "cement")
    base = cem.demand["cement"](2025)
    assert cem.demand["cement"](2026) == pytest.approx(base * 0.93, rel=1e-6)
    pt = next(s for s in inp.sites if s.name == "Port Talbot Steelworks")
    assert pt.demand["steel"](2026) == pytest.approx(0.6, rel=1e-6)
    assert pt.demand["steel"](2028) == pytest.approx(3.0, rel=1e-6)
    assert pt.demand["steel"](2035) == pytest.approx(3.0, rel=1e-6)
