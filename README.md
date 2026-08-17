# comitpy — industrial decarbonisation forecasting, rebuilt

A from-scratch Python successor to DESNZ's COMIT, keeping its proven
mechanics and none of its template. Direction set 16 Aug 2026:

- **This year's product: a 10-year forecast** (2026–2036, annual) of UK
  industrial energy, emissions and technology change.
- **Adaptable to net-zero pathways**: the same model runs with an
  emissions-cap trajectory (`pathways.py`) — a pathway is a named cap
  curve plus a policy pack, and pathways compose with price/policy
  scenarios in the ensemble runner.
- **Inputs are visible, traceable, adaptable**: plain CSVs in `datasets/`,
  one file per concept, every row carrying `source / retrieved / basis`
  (outturn | market | official | derived | judgement). The loader
  *refuses* untraceable rows — an untraceable input is a dummy value
  waiting to happen, which is what went wrong in the original. Editing a
  price pin or a technology parameter is editing a CSV.

## What was kept from COMIT (verified worth keeping)

The LP formulation: capacity transfer with residual decay, availability
factors, site-level production, annualised in-horizon capex (no terminal
cliff), traded/untraded carbon. Solver-level equivalence is **proven**:
this package's stack solves R-COMIT's exported 700k-variable LP to the
same objective at machine precision (rel diff 2e-15) with all 564
material tech-year totals matching (`parity.py`, phase A).

## What was rebuilt better (each proven valuable in the comit-harness evaluation)

Import/closure margin (domestic output can fall; leakage visible) ·
configurable windows · per-sector hurdle rates (0.20 default, calibrated
against 2021–25 UK ETS outturn) · adoption ramps · committed builds as
bounds (`BuildOrder`) · ensemble-first running · rolling-horizon mode ·
indexed-MAPE skill scoring · band-differentiated prices from a decomposed
wholesale+network+levies+margin stack (EII exemptions are a component,
not a fudge).

## The data (real, current, sourced)

`datasets/sites.csv` — **the v2 universe: all UK industry**, anchored to
the DESNZ territorial industry total (~46.5 Mt in 2025), in five layers
(`layer` column): top-100 ETS installations named (2025 verified
emissions), ETS tail aggregated (traded), NAEI non-traded point sources
≥10 kt named (2023 vintage scaled to 2025 by crosswalk sector ratios),
their tail aggregated, and a diffuse remainder to the anchor. A
double-count guard keeps NAEI rows naming parts of ETS complexes out;
the hindcast stays scored on the ETS-verified core, where outturn exists.
`fuel_prices.csv` — Aug-2026 market forwards spliced into central
projections. `carbon.csv` — UKA outturn/futures + linkage-converged EUA
consensus. `fuel_emissions.csv` — real grid-decarbonisation trajectory.
`technologies.csv` — starter set (Port Talbot EAF parameters are from the
actual project). `finance.csv` — backcast-calibrated hurdle rates.
Regenerate sites: `python scripts/build_sites_dataset.py` (reads the
harness's registry data).

## Run

```
pip install -e .[dev]
pytest tests            # 22 tests, every feature proven to bind
python run_forecast.py  # the 10-year forecast + a net-zero-2050 pathway
```

## Honest v0 boundaries

- Site demand is emissions-implied (v0 derivation, tagged); replace with
  real production/output data as the first upgrade.
- The technology roster is a starter set with indicative costs (tagged
  judgement) — sufficient for architecture and direction, not for
  quantitative pathway costs; the pathway mode's cost figures are
  placeholder until the zero-carbon roster (CCS variants, hydrogen supply
  caps, cluster timing) is carried over from the harness libraries.
- ~~Imports lack an explicit CBAM component~~ — built: CBAM = embodied
  emissions × traded carbon × phase curve on covered imports
  (`imports.csv`, `carbon.csv` cbam_phase; test-enforced that it closes
  the cement import leak).
- Validation gates: **both passed.** Solver parity: R-COMIT's exported
  700k-variable LP solved to the same objective at rel diff 2e-15
  (`parity.py`). Backcast skill: 2021–25 on this package's own pipeline
  (`run_backcast.py`, historical datasets in `datasets_backcast/`) scores
  **20.8% indexed MAPE vs the calibrated R fork's ~24.0%** on the same
  outturn shape — the improvement attributable to the import margin
  (cement yields to imports in the 2022 gas spike, as reality did).
  Residual error decomposed to the two known missing behaviours; the
  first is now built: **usage inertia** — a soft disruption cost on
  year-on-year usage reductions (`usage_inertia_cost`, GBP36m/PJ in
  `finance.csv`, calibrated against the backcast's 2022 dip signature).
  With it, the fake 2022 transient disappears (flat 99.9 profile) and
  the residual is the strategic-closure gap — now also built:
  **committed events** (`Closure`, `datasets_backcast/committed_events.csv`)
  — registry-corroborated closures (left the scheme AND emissions
  collapsed) plus the sourced strategic facts (Port Talbot BF/BOS,
  Grangemouth Refining, Lindsey). A closure zeroes the site's demand
  (its process-energy service vanished — no phantom redistribution) and
  is exempt from inertia charges (boardroom decisions are not market
  responses; test-enforced on a single-site micro-case). And the final increment is in:
  **real production data** (`sector_output.csv` — ONS IoP, crude-steel
  and MPA cement series as 2021=100 indices scaling site demand; steel
  held at its pre-closure level from 2024 so the Port Talbot event is
  not double-counted). **Hindcast skill: 4.1% indexed MAPE** — the full
  progression being calibrated R fork ~24% → v0 20.8% → inertia (shape
  fix) → events 13.3% → production data 4.1%, with 2023 essentially
  exact (89.4 vs 89.0). Stated honestly: conditional skill (events and
  outturn output known); the residual is timing granularity (three
  sectors, annual event boundaries vs partial-year closures).
  The forward counterpart is in too: `datasets/sector_output.csv`
  (2025=100 projections — MPA's no-recovery cement reality, flat-central
  EI manufacturing, steel flat with Scunthorpe deliberately unguessed)
  plus `datasets/site_overrides.csv`, explicit site-level demand pins
  that outrank sector trends — the Port Talbot EAF restart (0.6 Mt
  residual → 3.0 Mt nameplate from 2028), which fixes the built-but-idle
  EAF inconsistency: 2036 electricity use rises 4.1 → 10.5 PJ as the
  furnace actually runs. And the heterogeneity refinement is in:
  per-site `inertia_factor` (sites.csv — band base × size-rank gradient,
  deterministic and provenance-tagged), which grades the aggregate
  inertia response instead of the LP's all-or-nothing corner
  (test-enforced: a mid-range cost splits heterogeneous sites, never
  identical ones). Building it exposed and closed a genuine loophole:
  perfect foresight could dodge the inertia charge entirely by
  pre-switching in the first model year, so t0 is now charged against
  the incumbent's implied baseline. Hindcast: **3.7% indexed MAPE**,
  2025 endpoint exact (69.3 vs 69.2).
