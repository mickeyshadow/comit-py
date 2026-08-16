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
- Validation gates: solver parity DONE (2e-15); next is the 2021–25
  backcast skill gate on this package's own data pipeline (`skill.py`
  mirrors the harness method).
