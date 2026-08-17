"""One tidy results frame - single producer, every consumer reads it.

The dashboard (and anything else downstream) reads ONE long-format table
with consistent keys, instead of growing a parser per report CSV - parsers
per shape is how consumers drift. Schema:

    run      scenario name ("central", "gas_up50", "netzero_2050", ...)
    year     model year
    site     site name (sites.csv key)
    sector   heat | steel | cement
    layer    coverage layer (ets_named ... diffuse)
    cluster  industrial cluster
    variable emissions_ktco2e | fuel_use_pj | capacity_used_units |
             capacity_new_units
    detail   the fuel (fuel_use_pj) or technology (capacity_*) named by the
             row; "" for emissions
    value    the number

Site metadata is denormalised onto every row on purpose: a slice filtered
by layer or cluster must never need a join a consumer could get wrong.
"""
from __future__ import annotations

import pandas as pd

from .reporting import site_fuel_use

COLUMNS = ["run", "year", "site", "sector", "layer", "cluster",
           "variable", "detail", "value"]


def solution_frame(run: str, inp, sol,
                   layer_of: dict[str, str] | None = None) -> pd.DataFrame:
    """Flatten one solved run into the tidy schema."""
    layer_of = layer_of or {}
    sector_of = {s.name: s.sector for s in inp.sites}
    cluster_of = {s.name: s.cluster for s in inp.sites}

    parts = []
    emis = sol.emissions.rename(columns={"ktCO2e": "value"}).copy()
    emis["variable"], emis["detail"] = "emissions_ktco2e", ""
    parts.append(emis)

    fuel = (site_fuel_use(sol, inp.technologies)
            .rename(columns={"fuel": "detail", "PJ": "value"}))
    fuel["variable"] = "fuel_use_pj"
    parts.append(fuel)

    for var, df in (("capacity_used_units", sol.used),
                    ("capacity_new_units", sol.new)):
        d = df.rename(columns={"tech": "detail", "units": "value"}).copy()
        d = d[d.value > 1e-9]
        d["variable"] = var
        parts.append(d)

    out = pd.concat(parts, ignore_index=True)
    out["run"] = run
    out["sector"] = out.site.map(sector_of)
    out["layer"] = out.site.map(layer_of).fillna("")
    out["cluster"] = out.site.map(cluster_of)
    return out[COLUMNS]
