"""A toy-but-realistic UK slice used by the tests and as the API demo:
three sites in two bands, gas vs electric heat vs an import margin, priced
from the harness's central curves (comit-harness results/FORWARD-RUNS.md)."""
from __future__ import annotations

from .inputs import (BuildOrder, Fuel, ImportOption, Inputs, PriceStack, Site,
                     Technology, Window, pins)


def toy_inputs() -> Inputs:
    window = Window(2025, 2050, 5)

    gas = Fuel("gas", PriceStack(
        wholesale=pins({2025: 9.0, 2028: 8.0, 2050: 7.5}),
        network=pins({2025: 1.3}), levies=pins({2025: 0.0}),
        margin=pins({2025: 0.6}),
        band_factors={"small": {"margin": 3.0, "network": 1.5}}),
        emissions_ktco2e_per_pj=pins({2025: 51.2}))

    elec = Fuel("electricity", PriceStack(
        wholesale=pins({2025: 22.8, 2030: 20.8, 2045: 18.0}),
        network=pins({2025: 10.0}), levies=pins({2025: 12.0}),
        margin=pins({2025: 3.0}),
        band_factors={"large": {"levies": 0.2},        # EII exemptions
                      "small": {"margin": 2.0}}),
        emissions_ktco2e_per_pj=pins({2025: 35.0, 2030: 16.7, 2045: 2.8}))

    gas_boiler = Technology(
        "gas_boiler", "heat", "heat", capex_per_unit=8.0,
        fixed_opex_per_unit=0.3, lifetime=20, fuel_use={"gas": 1.11})
    elec_boiler = Technology(
        "elec_boiler", "heat", "heat", capex_per_unit=9.0,
        fixed_opex_per_unit=0.3, lifetime=20, fuel_use={"electricity": 1.02})
    eaf = Technology(
        "eaf", "steel", "steel", capex_per_unit=60.0,
        fixed_opex_per_unit=1.5, lifetime=25, fuel_use={"electricity": 2.2},
        first_year=2030)
    bof = Technology(
        "bof", "steel", "steel", capex_per_unit=40.0,
        fixed_opex_per_unit=1.2, lifetime=25, fuel_use={"gas": 3.0},
        process_emissions=120.0)

    sites = [
        Site("BigChem", "heat", band="large", traded=True,
             demand={"heat": pins({2025: 10.0, 2050: 9.0})},
             start_capacity={"gas_boiler": 12.0}),
        Site("SmallFood", "heat", band="small", traded=False,
             demand={"heat": pins({2025: 2.0})},
             start_capacity={"gas_boiler": 2.5}),
        Site("Steelworks", "steel", band="large", traded=True,
             demand={"steel": pins({2025: 3.0})},
             start_capacity={"bof": 3.5}),
    ]

    return Inputs(
        window=window,
        fuels={"gas": gas, "electricity": elec},
        technologies={t.name: t for t in (gas_boiler, elec_boiler, eaf, bof)},
        sites=sites,
        carbon_price_traded=pins({2025: 0.050, 2030: 0.120, 2050: 0.260}),
        carbon_price_untraded=pins({2025: 0.005}),
        hurdle_rates={"default": 0.20},
        imports=[ImportOption("steel", price=pins({2025: 55.0}))],
        build_orders=[BuildOrder("Steelworks", "eaf", 2030, min_units=3.0)],
    )
