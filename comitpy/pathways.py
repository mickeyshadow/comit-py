"""Named net-zero pathways = an emissions-cap trajectory + a policy pack.

A pathway is just a transform of Inputs (same shape the ensemble runner
takes), so pathways and price/policy scenarios compose: e.g.
netzero_2050 x cheap_electricity is one ensemble cell.
"""
from __future__ import annotations

from .inputs import Inputs, pins


def _cap_from(base_ktco2e: float, start: int, zero_year: int):
    return pins({start: base_ktco2e, zero_year: 0.0})


def netzero_2050(base_ktco2e: float, start: int = 2026):
    """Linear decline to zero territorial industrial emissions by 2050."""
    def apply(inp: Inputs) -> Inputs:
        return inp.with_(emissions_cap=_cap_from(base_ktco2e, start, 2050))
    return apply


def netzero_2045(base_ktco2e: float, start: int = 2026):
    def apply(inp: Inputs) -> Inputs:
        return inp.with_(emissions_cap=_cap_from(base_ktco2e, start, 2045))
    return apply


def carbon_budget(pin_points: dict[int, float]):
    """Arbitrary cap trajectory (e.g. CB6/CB7-consistent industry shares)."""
    def apply(inp: Inputs) -> Inputs:
        return inp.with_(emissions_cap=pins(pin_points))
    return apply
