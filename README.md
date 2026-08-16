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

`datasets/sites.csv` — 100 named installations + dispersed aggregates from
the UK ETS registry's 2025 verified emissions (not NAEI-2021).
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
pytest tests            # 13 tests, every feature proven to bind
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
- Imports lack an explicit CBAM component (add to `ImportOption` price).
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
  responses; test-enforced on a single-site micro-case). **Hindcast
  skill: 13.3% indexed MAPE** (v0 20.8% → inertia 21.0%-right-shaped →
  events 13.3%; calibrated R fork ~24%). Stated honestly: a hindcast fed
  known events measures *conditional* skill — the behavioural ceiling —
  and the remaining gap (99 vs 89-81 in 2022-24) is gradual output
  decline at surviving sites, which is the real-production-data
  increment. Caveat: uniform site economics make the inertia response
  binary (LP corners); per-site heterogeneity is the smoothing
  refinement.
