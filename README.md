# comitpy — the COMIT rebuild, designed as a forecaster

A Python rebuild of DESNZ's COMIT industrial decarbonisation model,
started 16 Aug 2026 from one day's evaluation of the R original
(`comit-harness` repo, `results/CODE-IMPROVEMENTS.md`). The premise: the
original is a 2050 pathway *optimiser*; this is built to be a 10-year
*forecaster*, with everything that was a retrofit there designed in here.

## The nine features, and where they live

| # | Feature (proven in the harness) | Where |
|---|---|---|
| 1 | Import/closure margin — domestic output can fall; leakage visible | `ImportOption`, national balance in `model.py` |
| 2 | Windowing — start/end/timestep are config; annualised capex means no terminal cliff | `Window` |
| 3 | Per-sector commercial hurdle rates | `Inputs.hurdle_rates`, capex annualisation in `model.py` |
| 4 | Adoption ramps (S-curve realism) | `Technology.ramp_limit` |
| 5 | Committed builds as variable bounds (Port Talbot-class facts) | `BuildOrder` |
| 6 | Ensemble-first running; ranges as the product | `ensemble.py` |
| 7 | Rolling-horizon (myopic) mode | `rolling.py` |
| 8 | Forecast-skill scoring (indexed-trajectory MAPE) | `skill.py` |
| 9 | Band-differentiated prices from a decomposed wholesale+network+levies+margin stack | `PriceStack` |

Every feature has a test proving it *binds* (`tests/test_core.py`) — the
harness's central lesson being that an unverified feature is a silent no-op.

## Status — honest

Working LP core (HiGHS via scipy) with the R-COMIT formulation: capacity
transfer with linear residual decay, availability factors, site production
with a national import-closing balance, annualised-loan capex at sector
hurdle rates, band-priced fuels, traded/untraded carbon. 10 tests green on
a toy UK slice (`examples.py`) priced from the harness's central curves.

**Not yet done:** ingesting the real COMIT input template (sites,
technologies, constraint tabs); H2/CO2 infrastructure networks (clusters,
pipes, storage); the dummy-sector conversion mechanisms (multi-variant
hydrogen, biomethane certificates). These are the next milestones.

## Validation gate

The rebuild is not trusted until:
1. **Parity**: on COMIT's own template (windowed, features off) it
   reproduces R-COMIT's objective and national tech-year totals within
   tolerance — the harness's solution fingerprints are the reference.
2. **Skill**: the 2021–2025 backcast scores at least as well as the
   calibrated R fork on the UK ETS outturn (harness `07_backcast_score.R`
   method, mirrored in `skill.py`).

## Run

```
pip install -e .[dev]
pytest tests
```
