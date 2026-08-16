"""A committed closure must zero the site from its year, leave others
untouched, and charge no inertia cost on the wind-down."""
import pytest

from comitpy import solve
from comitpy.examples import toy_inputs
from comitpy.inputs import Closure


def test_closure_zeroes_site_from_year():
    inp = toy_inputs().with_(closures=[Closure("BigChem", 2035)])
    sol = solve(inp)
    big = sol.used.query("site == 'BigChem'")
    assert big.query("year >= 2035").units.sum() == pytest.approx(0.0, abs=1e-8)
    assert big.query("year < 2035").units.sum() > 0
    small = sol.used.query("site == 'SmallFood' and year >= 2035")
    assert small.units.sum() > 0, "other sites unaffected"


def test_closure_does_not_pay_inertia():
    """Single-site micro-case: flat demand, one technology, a closure. The
    ONLY decline in the system is the exempt closure wind-down, so a huge
    inertia cost must leave the objective untouched."""
    from comitpy.inputs import (Fuel, Inputs, PriceStack, Site, Technology,
                                Window, pins)
    gas = Fuel("gas", PriceStack(wholesale=pins({2025: 10.0})),
               emissions_ktco2e_per_pj=pins({2025: 51.2}))
    boiler = Technology("boiler", "heat", "heat", capex_per_unit=8.0,
                        fixed_opex_per_unit=0.3, lifetime=40,
                        fuel_use={"gas": 1.11})
    site = Site("OnlySite", "heat", band="large", traded=True,
                demand={"heat": pins({2025: 5.0})},
                start_capacity={"boiler": 6.0})
    base = Inputs(window=Window(2025, 2045, 5), fuels={"gas": gas},
                  technologies={"boiler": boiler}, sites=[site],
                  carbon_price_traded=pins({2025: 0.05}),
                  carbon_price_untraded=pins({2025: 0.005}),
                  hurdle_rates={"default": 0.2},
                  closures=[Closure("OnlySite", 2040)])
    a = solve(base)
    b = solve(base.with_(usage_inertia_cost=1000.0))
    assert b.objective == pytest.approx(a.objective, rel=1e-6)
