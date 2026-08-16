"""Input data model.

Design principles (from the R-COMIT evaluation, results/CODE-IMPROVEMENTS.md
in the comit-harness repo): everything that was a retrofit there is an index
or a first-class field here.

- Prices are indexed by (fuel, year, band) and built from a decomposed
  wholesale + network + levies + margin stack, so policy levers are explicit
  components (item 9).
- The solve window (start, end, timestep) is configuration (item 2).
- Financing is per-sector: each sector carries its own hurdle rate (item 3).
- Imports are a native supply margin per demand commodity (item 1).
- Committed builds are bounds on new-capacity variables (item 5).
- National adoption ramps per technology class (item 4).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable


Curve = Callable[[int], float]


def pins(points: dict[int, float]) -> Curve:
    """Linear interpolation between pinned years, flat outside the range."""
    years = sorted(points)

    def f(y: int) -> float:
        if y <= years[0]:
            return points[years[0]]
        if y >= years[-1]:
            return points[years[-1]]
        for a, b in zip(years, years[1:]):
            if a <= y <= b:
                w = (y - a) / (b - a)
                return points[a] * (1 - w) + points[b] * w
        raise AssertionError
    return f


@dataclass(frozen=True)
class Window:
    """The solve window is configuration, not surgery (item 2)."""
    start: int
    end: int
    timestep: int = 1

    @property
    def years(self) -> list[int]:
        return list(range(self.start, self.end + 1, self.timestep))


@dataclass(frozen=True)
class PriceStack:
    """Retail price = wholesale + network + levies + margin, each a curve in
    GBPm/PJ, with per-band multipliers. Policy scenarios toggle components
    (e.g. levies to zero for EIIs) instead of scaling a single number."""
    wholesale: Curve
    network: Curve = field(default=lambda y: 0.0)
    levies: Curve = field(default=lambda y: 0.0)
    margin: Curve = field(default=lambda y: 0.0)
    band_factors: dict[str, dict[str, float]] = field(default_factory=dict)
    # band -> component -> multiplier; missing entries default to 1.

    def price(self, year: int, band: str) -> float:
        total = 0.0
        for name, curve in (("wholesale", self.wholesale), ("network", self.network),
                            ("levies", self.levies), ("margin", self.margin)):
            factor = self.band_factors.get(band, {}).get(name, 1.0)
            total += curve(year) * factor
        return total


@dataclass(frozen=True)
class Fuel:
    name: str
    stack: PriceStack
    emissions_ktco2e_per_pj: Curve  # can vary by year (e.g. grid electricity)


@dataclass(frozen=True)
class Technology:
    name: str
    sector: str
    output_commodity: str
    capex_per_unit: float           # GBPm per PJ/yr of capacity
    fixed_opex_per_unit: float      # GBPm per PJ/yr of capacity per year
    lifetime: int
    fuel_use: dict[str, float]      # fuel -> PJ input per PJ output
    availability: float = 0.9
    capture_rate: float = 0.0       # share of emissions captured (CCS)
    process_emissions: float = 0.0  # ktCO2e per PJ output, pre-capture
    first_year: int = 0
    ramp_limit: float | None = None  # national max new capacity per year (item 4)


@dataclass(frozen=True)
class Site:
    name: str
    sector: str
    band: str                        # price band: e.g. "large", "small" (item 9)
    traded: bool                     # UK ETS exposure (carbon price applied)
    demand: dict[str, Curve]         # commodity -> PJ/yr required
    start_capacity: dict[str, float] = field(default_factory=dict)  # tech -> units


@dataclass(frozen=True)
class ImportOption:
    """The import/closure margin (item 1): national demand may be met by
    imports at a delivered price; imported volumes carry no territorial
    emissions, which is how leakage becomes visible."""
    commodity: str
    price: Curve                     # GBPm/PJ delivered (CBAM enters here)


@dataclass(frozen=True)
class BuildOrder:
    """A committed real-world build (item 5): bounds on new capacity."""
    site: str
    tech: str
    year: int
    min_units: float = 0.0
    max_units: float | None = None


@dataclass(frozen=True)
class Inputs:
    window: Window
    fuels: dict[str, Fuel]
    technologies: dict[str, Technology]
    sites: list[Site]
    carbon_price_traded: Curve
    carbon_price_untraded: Curve
    hurdle_rates: dict[str, float]   # sector -> financing rate (item 3)
    discount_rate: float = 0.035
    imports: list[ImportOption] = field(default_factory=list)
    build_orders: list[BuildOrder] = field(default_factory=list)

    def hurdle(self, sector: str) -> float:
        return self.hurdle_rates.get(sector, self.hurdle_rates.get("default", 0.2))

    def with_(self, **kw) -> "Inputs":
        """Scenario copies for the ensemble runner (item 6)."""
        return replace(self, **kw)
