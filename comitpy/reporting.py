"""Shared report helpers - defined once, used by every report script."""
import pandas as pd

EPS = 1e-3

UNIVERSE_NOTE = (
    "**v2 universe - all UK industry**, anchored to the DESNZ territorial\n"
    "industry total (~46.5 Mt in 2025), in five transparent layers: the\n"
    "top-100 ETS installations named, the ETS tail aggregated, NAEI\n"
    "non-traded point sources >=10 kt named, their tail aggregated, and a\n"
    "diffuse remainder. The hindcast (skill score) stays defined on the\n"
    "ETS-verified core, where annual outturn exists.")


def site_fuel_use(sol, technologies) -> pd.DataFrame:
    """Per (site, year, fuel) PJ: usage x technology fuel intensities."""
    tech_fuels = {name: t.fuel_use for name, t in technologies.items()}
    rows = []
    for _, r in sol.used.iterrows():
        for fuel, use in tech_fuels[r.tech].items():
            rows.append((r.site, r.year, fuel, r.units * use))
    return (pd.DataFrame(rows, columns=["site", "year", "fuel", "PJ"])
            .groupby(["site", "year", "fuel"], as_index=False).sum())


def transitions(sol, window_start: int) -> list[tuple]:
    """(site, tech, first_year_used) for technologies arriving inside the
    window - the site-level technology-change events."""
    out = []
    for (site, tech), g in sol.used.groupby(["site", "tech"]):
        g = g[g.units > EPS]
        if g.empty:
            continue
        first = int(g.year.min())
        if first > window_start:
            out.append((site, tech, first))
    return out
