"""LP core: the proven R-COMIT formulation (capacity transfer, availability,
production balance, annualised-loan capex) with the harness-proven features
native: per-sector hurdle rates, band pricing, an import margin, adoption
ramps and committed-build bounds.

Solved with HiGHS via scipy.optimize.linprog (sparse).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import linprog

from .inputs import Inputs, Technology


def pmt(principal: float, rate: float, n: int) -> float:
    """Annualised loan payment, mirroring R-COMIT's PMT."""
    if rate <= 0:
        return principal / n
    f = (1 + rate) ** n
    return principal * rate * f / (f - 1)


def emissions_per_unit(tech: Technology, inputs: Inputs, year: int) -> float:
    """ktCO2e released per PJ of output (post-capture)."""
    fuel_emis = sum(use * inputs.fuels[f].emissions_ktco2e_per_pj(year)
                    for f, use in tech.fuel_use.items())
    return (fuel_emis + tech.process_emissions) * (1 - tech.capture_rate)


@dataclass
class Solution:
    status: str
    objective: float
    used: pd.DataFrame        # site, tech, year, units (PJ output)
    new: pd.DataFrame         # site, tech, year, units of new capacity
    imports: pd.DataFrame     # commodity, year, PJ
    emissions: pd.DataFrame   # site, year, ktCO2e (territorial)
    fuel_use: pd.DataFrame    # fuel, year, PJ


class ModelBuilder:
    def __init__(self, inputs: Inputs):
        self.inp = inputs
        self.years = inputs.window.years
        self.dt = inputs.window.timestep
        self.var_names: list[str] = []
        self.cost = []
        self.lb = []
        self.ub = []
        self.idx: dict[tuple, int] = {}

    def add_var(self, key: tuple, cost: float, lb: float = 0.0,
                ub: float = np.inf) -> int:
        i = len(self.var_names)
        self.idx[key] = i
        self.var_names.append("|".join(map(str, key)))
        self.cost.append(cost)
        self.lb.append(lb)
        self.ub.append(ub)
        return i

    # -- variable creation ----------------------------------------------------

    def build_variables(self):
        inp, years = self.inp, self.years
        disc = {t: 1 / (1 + inp.discount_rate) ** (t - years[0]) for t in years}
        self.disc = disc

        orders = {(o.site, o.tech, o.year): o for o in inp.build_orders}

        for s in inp.sites:
            techs = [j for j in inp.technologies.values() if j.sector == s.sector]
            for j in techs:
                for t in years:
                    # new capacity: annualised payments within the horizon at
                    # the SECTOR hurdle rate (items 2+3: no terminal cliff,
                    # commercial financing)
                    rate = inp.hurdle(s.sector)
                    payment = pmt(j.capex_per_unit, rate, j.lifetime)
                    horizon_payments = sum(
                        payment * self.dt * disc[tau]
                        for tau in years if t <= tau < t + j.lifetime)
                    o = orders.get((s.name, j.name, t))
                    lb = o.min_units if o else 0.0
                    ub = (o.max_units if o and o.max_units is not None else np.inf)
                    if t < j.first_year:
                        ub = lb  # not yet available (allow forced builds only)
                    self.add_var(("N", s.name, j.name, t), horizon_payments, lb, ub)
                    self.add_var(("A", s.name, j.name, t),
                                 j.fixed_opex_per_unit * self.dt * disc[t])
                    # used capacity: fuel (band-priced, item 9) + carbon
                    fuel_cost = sum(
                        use * inp.fuels[f].stack.price(t, s.band)
                        for f, use in j.fuel_use.items())
                    cprice = (inp.carbon_price_traded(t) if s.traded
                              else inp.carbon_price_untraded(t))
                    carbon = emissions_per_unit(j, inp, t) * cprice
                    self.add_var(("U", s.name, j.name, t),
                                 (fuel_cost + carbon) * self.dt * disc[t])

        for imp in inp.imports:
            for t in years:
                self.add_var(("M", imp.commodity, t),
                             imp.price(t) * self.dt * disc[t])

    # -- constraints ----------------------------------------------------------

    def build_constraints(self):
        inp, years = self.inp, self.years
        rows_eq, rhs_eq, rows_ub, rhs_ub = [], [], [], []

        def coef_row(entries):
            r = {}
            for key, v in entries:
                r[self.idx[key]] = r.get(self.idx[key], 0.0) + v
            return r

        for s in inp.sites:
            techs = [j for j in inp.technologies.values() if j.sector == s.sector]
            for j in techs:
                start = s.start_capacity.get(j.name, 0.0)
                for t in years:
                    # capacity transfer: A = residual (linear decay) + sum of
                    # in-life builds
                    residual = start * max(0.0, 1 - (t - years[0]) / j.lifetime)
                    entries = [(("A", s.name, j.name, t), 1.0)]
                    entries += [(("N", s.name, j.name, tp), -1.0)
                                for tp in years if tp <= t < tp + j.lifetime]
                    rows_eq.append(coef_row(entries))
                    rhs_eq.append(residual)
                    # availability: U <= af * A
                    rows_ub.append(coef_row([(("U", s.name, j.name, t), 1.0),
                                             (("A", s.name, j.name, t),
                                              -j.availability)]))
                    rhs_ub.append(0.0)

        # production: each site may serve at most its own demand; the national
        # balance closes with imports (item 1). Without an import option the
        # site inequality + national equality forces site-level supply.
        importables = {i.commodity for i in inp.imports}
        commodities = {c for s in inp.sites for c in s.demand}
        for c in commodities:
            for t in years:
                nat_entries = []
                nat_demand = 0.0
                for s in inp.sites:
                    if c not in s.demand:
                        continue
                    d = s.demand[c](t)
                    nat_demand += d
                    site_entries = [(("U", s.name, j.name, t), 1.0)
                                    for j in inp.technologies.values()
                                    if j.sector == s.sector
                                    and j.output_commodity == c]
                    if site_entries:
                        rows_ub.append(coef_row(site_entries))
                        rhs_ub.append(d)
                        nat_entries += site_entries
                if c in importables:
                    nat_entries.append((("M", c, t), 1.0))
                rows_eq.append(coef_row(nat_entries))
                rhs_eq.append(nat_demand)

        # adoption ramps (item 4): national new-build cap per tech per year
        for j in inp.technologies.values():
            if j.ramp_limit is None:
                continue
            for t in years:
                entries = [(("N", s.name, j.name, t), 1.0)
                           for s in inp.sites if s.sector == j.sector]
                if entries:
                    rows_ub.append(coef_row(entries))
                    rhs_ub.append(j.ramp_limit * self.dt)

        self.rows_eq, self.rhs_eq = rows_eq, rhs_eq
        self.rows_ub, self.rhs_ub = rows_ub, rhs_ub

    # -- assemble + solve -----------------------------------------------------

    def to_sparse(self, rows):
        data, ri, ci = [], [], []
        for k, r in enumerate(rows):
            for i, v in r.items():
                ri.append(k); ci.append(i); data.append(v)
        return sparse.coo_matrix((data, (ri, ci)),
                                 shape=(len(rows), len(self.var_names))).tocsr()

    def solve(self) -> Solution:
        self.build_variables()
        self.build_constraints()
        res = linprog(
            c=np.array(self.cost),
            A_ub=self.to_sparse(self.rows_ub), b_ub=np.array(self.rhs_ub),
            A_eq=self.to_sparse(self.rows_eq), b_eq=np.array(self.rhs_eq),
            bounds=list(zip(self.lb, self.ub)), method="highs")
        if not res.success:
            raise RuntimeError(f"solve failed: {res.message}")
        x = res.x
        inp = self.inp

        recs = {"U": [], "N": [], "M": []}
        for key, i in self.idx.items():
            if x[i] > 1e-9 and key[0] in recs:
                recs[key[0]].append(key[1:] + (x[i],))
        used = pd.DataFrame(recs["U"], columns=["site", "tech", "year", "units"])
        new = pd.DataFrame(recs["N"], columns=["site", "tech", "year", "units"])
        imports = pd.DataFrame(recs["M"], columns=["commodity", "year", "PJ"])

        emis_rows, fuel_rows = [], []
        for _, r in used.iterrows():
            j = inp.technologies[r.tech]
            emis_rows.append((r.site, r.year,
                              r.units * emissions_per_unit(j, inp, r.year)))
            for f, use in j.fuel_use.items():
                fuel_rows.append((f, r.year, r.units * use))
        emissions = (pd.DataFrame(emis_rows, columns=["site", "year", "ktCO2e"])
                     .groupby(["site", "year"], as_index=False).sum())
        fuel_use = (pd.DataFrame(fuel_rows, columns=["fuel", "year", "PJ"])
                    .groupby(["fuel", "year"], as_index=False).sum())
        return Solution("optimal", res.fun, used, new, imports, emissions,
                        fuel_use)


def solve(inputs: Inputs) -> Solution:
    return ModelBuilder(inputs).solve()
