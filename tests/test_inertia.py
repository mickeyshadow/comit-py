"""The usage-inertia cost must bind (damp a price-spike dip) and must not
break pathway feasibility."""
import dataclasses

from comitpy import Window, pins, solve
from comitpy.examples import toy_inputs
from comitpy.inputs import Fuel, PriceStack
from comitpy.pathways import netzero_2050


def spiked_inputs():
    """Toy with a mid-window gas price spike (2035 3x) to provoke a dip."""
    inp = toy_inputs().with_(window=Window(2025, 2045, 5))
    fuels = dict(inp.fuels)
    g = fuels["gas"]
    fuels["gas"] = Fuel("gas", PriceStack(
        pins({2025: 9.0, 2030: 9.0, 2035: 60.0, 2040: 9.0}),
        g.stack.network, g.stack.levies, g.stack.margin, g.stack.band_factors),
        g.emissions_ktco2e_per_pj)
    return inp.with_(fuels=fuels,
                     carbon_price_traded=pins({2025: 0.05}))


def gas_dip(sol):
    u = (sol.used.query("tech == 'gas_boiler'")
         .groupby("year").units.sum())
    return float(u.get(2030, 0.0) - u.get(2035, 0.0))


def test_inertia_damps_the_dip():
    # the toy spike lasts a full 5-year period, so the one-off disruption
    # cost must exceed ~5 years of fuel saving (~GBP100m/PJ) to bind
    free = solve(spiked_inputs())
    held = solve(spiked_inputs().with_(usage_inertia_cost=250.0))
    assert gas_dip(held) < gas_dip(free) - 1e-6, \
        "a strong disruption cost should keep gas burning through the spike"


def test_inertia_keeps_pathways_feasible():
    inp = spiked_inputs().with_(usage_inertia_cost=50.0)
    base = float(solve(inp).emissions.query("year == 2025").ktCO2e.sum())
    capped = solve(netzero_2050(base, start=2025)(inp))
    assert capped.status == "optimal"
    late = capped.emissions.query("year == 2045").ktCO2e.sum()
    cap_2045 = base * (1 - 0.95 * (2045 - 2025) / 25)
    assert late <= cap_2045 + 1e-6
