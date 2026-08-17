"""The named ensemble worlds - one lever each - shared by every report so
scenario definitions exist in exactly one place."""
import dataclasses

from .inputs import Fuel, Inputs, PriceStack


def scale_fuel(inp: Inputs, fuel: str, component: str, factor: float) -> Inputs:
    f = inp.fuels[fuel]
    st = f.stack
    parts = {c: getattr(st, c) for c in ("wholesale", "network", "levies",
                                         "margin")}
    old = parts[component]
    parts[component] = (lambda y, _o=old: _o(y) * factor)
    fuels = dict(inp.fuels)
    fuels[fuel] = Fuel(f.name, PriceStack(parts["wholesale"], parts["network"],
                                          parts["levies"], parts["margin"],
                                          st.band_factors),
                       f.emissions_ktco2e_per_pj)
    return inp.with_(fuels=fuels)


def scale_carbon(inp: Inputs, factor: float) -> Inputs:
    c = inp.carbon_price_traded
    return inp.with_(carbon_price_traded=lambda y, _c=c: _c(y) * factor)


def slip_ccs(inp: Inputs) -> Inputs:
    techs = dict(inp.technologies)
    for name in ("cement_kiln_ccs", "gas_boiler_ccs"):
        t = techs[name]
        techs[name] = dataclasses.replace(
            t, first_year=t.first_year + 4,
            ramp_limit=(t.ramp_limit or 0) * 0.5 or None)
    return inp.with_(technologies=techs)


WORLDS = {
    "levies_off": lambda i: scale_fuel(i, "electricity", "levies", 0.0),
    "gas_up50": lambda i: scale_fuel(i, "gas", "wholesale", 1.5),
    "gas_down30": lambda i: scale_fuel(i, "gas", "wholesale", 0.7),
    "carbon_x1.5": lambda i: scale_carbon(i, 1.5),
    "carbon_x0.6": lambda i: scale_carbon(i, 0.6),
    "ccs_slip": slip_ccs,
}
