"""Heterogeneous inertia factors must turn the binary aggregate response
into a graded one: at a cost near the common breakeven, low-factor sites
swing while high-factor sites hold."""
import dataclasses

import pytest

from comitpy import Window, pins, solve
from comitpy.inputs import Fuel, Inputs, PriceStack, Site, Technology


def three_site_system(factors):
    gas = Fuel("gas", PriceStack(
        wholesale=pins({2021: 9.0, 2022: 27.0, 2023: 9.0})),
        emissions_ktco2e_per_pj=pins({2021: 51.2}))
    bio = Fuel("biomass", PriceStack(wholesale=pins({2021: 8.0})),
               emissions_ktco2e_per_pj=pins({2021: 0.0}))
    gas_b = Technology("gas_b", "heat", "heat", capex_per_unit=8.0,
                       fixed_opex_per_unit=0.3, lifetime=20,
                       fuel_use={"gas": 1.11})
    bio_b = Technology("bio_b", "heat", "heat", capex_per_unit=8.0,
                       fixed_opex_per_unit=0.3, lifetime=20,
                       fuel_use={"biomass": 1.18})
    sites = [Site(f"S{i}", "heat", band="mid", traded=False,
                  demand={"heat": pins({2021: 5.0})},
                  start_capacity={"gas_b": 6.0}, inertia_factor=f)
             for i, f in enumerate(factors)]
    return Inputs(window=Window(2021, 2025, 1),
                  fuels={"gas": gas, "biomass": bio},
                  technologies={"gas_b": gas_b, "bio_b": bio_b},
                  sites=sites,
                  carbon_price_traded=pins({2021: 0.05}),
                  carbon_price_untraded=pins({2021: 0.004}),
                  hurdle_rates={"default": 0.2})


def spike_swing(sol, site):
    u = sol.used.query(f"site == '{site}' and tech == 'gas_b'")
    y21 = u.query("year == 2021").units.sum()
    y22 = u.query("year == 2022").units.sum()
    return y21 - y22


def find_partial_cost():
    """The graded property: some cost splits the sites - low-factor swings,
    high-factor holds."""
    for cost in (5, 10, 15, 20, 25, 30, 40):
        sol = solve(three_site_system([0.5, 1.0, 2.0])
                    .with_(usage_inertia_cost=float(cost)))
        s0 = spike_swing(sol, "S0")
        s2 = spike_swing(sol, "S2")
        if s0 > 0.5 and s2 < 0.1:
            return cost
    return None


def test_heterogeneity_grades_the_response():
    assert find_partial_cost() is not None, \
        "no cost splits the sites - the response is still binary"


def test_uniform_factors_stay_binary():
    """Control: with identical factors the same sweep never splits."""
    for cost in (5, 10, 15, 20, 25, 30, 40):
        sol = solve(three_site_system([1.0, 1.0, 1.0])
                    .with_(usage_inertia_cost=float(cost)))
        swings = [spike_swing(sol, s) for s in ("S0", "S1", "S2")]
        big = sum(1 for s in swings if s > 0.5)
        small = sum(1 for s in swings if s < 0.1)
        assert not (big and small), \
            "identical sites split asymmetrically - degeneracy, not economics"
