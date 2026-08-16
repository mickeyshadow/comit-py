"""Provenance-enforced input layer.

Requirements this implements (16 Aug 2026 direction): inputs must be
visible, traceable and adaptable. So:

- Inputs live as plain CSVs in a data directory, one file per concept
  (sites, technologies, fuel price pins, carbon, caps). Anyone can read
  them; git diffs them; a desk analyst edits a pin and re-runs.
- Every row carries `source`, `retrieved` and `basis` columns. basis is one
  of: outturn | market | official | derived | judgement. The loader REFUSES
  rows without them - an untraceable input is a silent dummy value, which
  is how the original model's template went wrong.
- Pins-in-CSV become interpolated curves, mirroring the harness convention.
"""
from __future__ import annotations

import os

import pandas as pd

from .inputs import (BuildOrder, Closure, Fuel, ImportOption, Inputs,
                     PriceStack, Site, Technology, Window, pins)

BASES = {"outturn", "market", "official", "derived", "judgement"}
PROV_COLS = ["source", "retrieved", "basis"]


def _check_provenance(df: pd.DataFrame, name: str) -> None:
    missing = [c for c in PROV_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"{name}: missing provenance columns {missing} - "
                         "every input row must be traceable")
    bad = df[df.basis.isna() | ~df.basis.isin(BASES) | df.source.isna()]
    if not bad.empty:
        raise ValueError(
            f"{name}: {len(bad)} rows lack valid provenance "
            f"(basis must be one of {sorted(BASES)}; source required). "
            f"First offender: {bad.iloc[0].to_dict()}")


def _read(path: str, name: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    _check_provenance(df, name)
    return df


def _curve_from(df: pd.DataFrame, key_cols: dict, value_col: str = "value"):
    sel = df
    for c, v in key_cols.items():
        sel = sel[sel[c] == v]
    sel = sel[sel.year.notna()]   # band-factor rows carry no year
    if sel.empty:
        raise ValueError(f"no pins for {key_cols}")
    return pins(dict(zip(sel.year.astype(int), sel[value_col].astype(float))))


def load_inputs(data_dir: str, window: Window) -> Inputs:
    fp = _read(os.path.join(data_dir, "fuel_prices.csv"), "fuel_prices")
    fe = _read(os.path.join(data_dir, "fuel_emissions.csv"), "fuel_emissions")
    cb = _read(os.path.join(data_dir, "carbon.csv"), "carbon")
    tech = _read(os.path.join(data_dir, "technologies.csv"), "technologies")
    sites = _read(os.path.join(data_dir, "sites.csv"), "sites")
    fin = _read(os.path.join(data_dir, "finance.csv"), "finance")

    fuels: dict[str, Fuel] = {}
    for f in fp.fuel.unique():
        components = {}
        for comp in ("wholesale", "network", "levies", "margin"):
            sel = fp[(fp.fuel == f) & (fp.component == comp)]
            components[comp] = (
                _curve_from(fp, {"fuel": f, "component": comp})
                if not sel.empty else pins({window.start: 0.0}))
        bands = {}
        bsel = fp[(fp.fuel == f) & fp.band_factor.notna()]
        for _, r in bsel.iterrows():
            bands.setdefault(r.band, {})[r.component] = float(r.band_factor)
        fuels[f] = Fuel(f, PriceStack(components["wholesale"],
                                      components["network"],
                                      components["levies"],
                                      components["margin"], bands),
                        _curve_from(fe, {"fuel": f}))

    technologies = {}
    for name, g in tech.groupby("technology"):
        row = g.iloc[0]
        fuel_use = {r.fuel: float(r.fuel_use)
                    for _, r in g.iterrows() if pd.notna(r.fuel)}
        technologies[name] = Technology(
            name=name, sector=row.sector, output_commodity=row.output,
            capex_per_unit=float(row.capex), fixed_opex_per_unit=float(row.opex),
            lifetime=int(row.lifetime), fuel_use=fuel_use,
            availability=float(row.availability),
            capture_rate=float(row.capture_rate),
            process_emissions=float(row.process_emissions),
            first_year=int(row.first_year),
            ramp_limit=(float(row.ramp_limit)
                        if pd.notna(row.ramp_limit) else None))

    # optional sector output indices (2021=100): scale every site's demand by
    # its sector's real production trajectory
    idx_curves: dict[str, object] = {}
    so_path = os.path.join(data_dir, "sector_output.csv")
    if os.path.exists(so_path):
        so = _read(so_path, "sector_output")
        for sector in so.sector.unique():
            idx_curves[sector] = _curve_from(so, {"sector": sector})

    # optional site-level demand overrides (e.g. the Port Talbot EAF restart):
    # explicit pins that REPLACE the sector-indexed curve for that site -
    # committed site facts outrank sector trends, no double counting
    overrides: dict[tuple[str, str], object] = {}
    ov_path = os.path.join(data_dir, "site_overrides.csv")
    if os.path.exists(ov_path):
        ov = _read(ov_path, "site_overrides")
        for (site, comm), g in ov.groupby(["site", "commodity"]):
            overrides[(site, comm)] = pins(
                dict(zip(g.year.astype(int), g.value.astype(float))))

    def demand_curve(site: str, commodity: str, base: float, sector: str):
        if (site, commodity) in overrides:
            return overrides[(site, commodity)]
        idx = idx_curves.get(sector)
        if idx is None:
            return pins({int(window.start): base})
        return lambda y: base * idx(y) / 100.0

    site_objs = []
    for _, r in sites.iterrows():
        site_objs.append(Site(
            name=r.site, sector=r.sector, band=r.band,
            traded=bool(r.traded),
            demand={r.commodity: demand_curve(r.site, r.commodity,
                                              float(r.demand_pj), r.sector)},
            start_capacity={r.incumbent_tech: float(r.start_capacity)},
            inertia_factor=(float(r.inertia_factor)
                            if "inertia_factor" in sites.columns
                            and pd.notna(r.inertia_factor) else 1.0)))

    hurdles = {r.sector: float(r.hurdle_rate)
               for _, r in fin.iterrows() if pd.notna(r.hurdle_rate)}
    default = fin[fin.sector == "default"].iloc[0]
    inertia = (float(default.usage_inertia_cost)
               if "usage_inertia_cost" in fin.columns
               and pd.notna(default.usage_inertia_cost) else 0.0)

    closures = []
    ev_path = os.path.join(data_dir, "committed_events.csv")
    if os.path.exists(ev_path):
        ev = _read(ev_path, "committed_events")
        closures = [Closure(r.site, int(r.from_year)) for _, r in ev.iterrows()]

    # imports.csv: the import/closure margin per commodity, with CBAM fields.
    # A commodity NOT listed cannot import - sites must serve it (no hacks).
    imports = []
    imp_path = os.path.join(data_dir, "imports.csv")
    if os.path.exists(imp_path):
        im = _read(imp_path, "imports")
        for commodity, g in im.groupby("commodity"):
            imports.append(ImportOption(
                commodity=commodity,
                price=pins(dict(zip(g.year.astype(int),
                                    g.price.astype(float)))),
                embodied_ktco2_per_unit=float(g.embodied_ktco2_per_unit.iloc[0]),
                cbam_covered=bool(g.cbam_covered.iloc[0])))

    # build_orders.csv: committed builds as variable bounds
    build_orders = []
    bo_path = os.path.join(data_dir, "build_orders.csv")
    if os.path.exists(bo_path):
        bo = _read(bo_path, "build_orders")
        for _, r in bo.iterrows():
            build_orders.append(BuildOrder(
                r.site, r.tech, int(r.year), float(r.min_units),
                float(r.max_units) if pd.notna(r.max_units) else None))

    # cbam_phase series (optional; default = no CBAM)
    cbam_phase = (lambda y: 0.0)
    if "cbam_phase" in set(cb.series):
        cbam_phase = _curve_from(cb, {"series": "cbam_phase"})

    return Inputs(
        window=window, fuels=fuels, technologies=technologies,
        sites=site_objs,
        carbon_price_traded=_curve_from(cb, {"series": "traded"}),
        carbon_price_untraded=_curve_from(cb, {"series": "untraded"}),
        hurdle_rates=hurdles,
        discount_rate=float(default.discount_rate),
        usage_inertia_cost=inertia,
        closures=closures,
        imports=imports,
        build_orders=build_orders,
        cbam_phase=cbam_phase,
    )
