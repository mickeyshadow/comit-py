"""Named net-zero pathways = an emissions-cap trajectory + a policy pack.

A pathway is just a transform of Inputs (same shape the ensemble runner
takes), so pathways and price/policy scenarios compose: e.g.
netzero_2050 x cheap_electricity is one ensemble cell.
"""
from __future__ import annotations

from .inputs import Inputs, pins


def _cap_from(base_ktco2e: float, start: int, target_year: int,
              residual_share: float):
    return pins({start: base_ktco2e,
                 target_year: base_ktco2e * residual_share})


def netzero_2050(base_ktco2e: float, start: int = 2026,
                 residual_share: float = 0.05):
    """Linear decline to a RESIDUAL by 2050, not absolute zero: net zero
    for industry means hard-to-abate residuals (capture slip, process
    remainders, near-zero grid factors) are offset by removals elsewhere
    in the economy. 5% residual is a CB-style judgement default - make it
    explicit rather than reaching zero through phantom mechanisms."""
    def apply(inp: Inputs) -> Inputs:
        return inp.with_(emissions_cap=_cap_from(base_ktco2e, start, 2050,
                                                 residual_share))
    return apply


def netzero_2045(base_ktco2e: float, start: int = 2026,
                 residual_share: float = 0.05):
    def apply(inp: Inputs) -> Inputs:
        return inp.with_(emissions_cap=_cap_from(base_ktco2e, start, 2045,
                                                 residual_share))
    return apply


def carbon_budget(pin_points: dict[int, float]):
    """Arbitrary cap trajectory (e.g. CB6/CB7-consistent industry shares)."""
    def apply(inp: Inputs) -> Inputs:
        return inp.with_(emissions_cap=pins(pin_points))
    return apply
