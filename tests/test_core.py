"""Each of the designed-in features must demonstrably bind — the harness
taught us that a feature that cannot be shown to bind is a silent no-op."""
import pandas as pd
import pytest

from comitpy import (Window, indexed_mape, pins, rolling_solve, run_ensemble,
                     solve, spread)
from comitpy.examples import toy_inputs
from comitpy.inputs import ImportOption


def test_core_solves_and_meets_demand():
    sol = solve(toy_inputs())
    assert sol.status == "optimal"
    heat_2025 = sol.used.query("year == 2025 and tech in ('gas_boiler', 'elec_boiler')")
    assert heat_2025.units.sum() == pytest.approx(12.0, rel=1e-4)


def test_import_margin_engages_when_domestic_expensive():
    inp = toy_inputs()
    cheap = inp.with_(imports=[ImportOption("steel", price=pins({2025: 5.0}))])
    sol = solve(cheap)
    assert sol.imports.PJ.sum() > 1.0, "cheap imports should displace domestic steel"
    dear = inp.with_(imports=[ImportOption("steel", price=pins({2025: 500.0}))])
    sol2 = solve(dear)
    assert sol2.imports.PJ.sum() < 0.5


def test_band_pricing_changes_who_switches():
    """Large band (EII levy exemptions) faces cheaper electricity than the
    small band; with a strong carbon signal the large traded site should
    electrify more readily than the small untraded one."""
    inp = toy_inputs()
    hot_carbon = inp.with_(carbon_price_traded=pins({2025: 0.6}))
    sol = solve(hot_carbon)
    big = sol.used.query("site == 'BigChem' and tech == 'elec_boiler'").units.sum()
    small = sol.used.query("site == 'SmallFood' and tech == 'elec_boiler'").units.sum()
    assert big > 0
    assert small == pytest.approx(0.0, abs=1e-6)


def test_build_order_binds():
    sol = solve(toy_inputs())
    eaf_built = sol.new.query("site == 'Steelworks' and tech == 'eaf' and year == 2030")
    assert not eaf_built.empty and eaf_built.units.iloc[0] >= 3.0 - 1e-6


def test_sector_hurdle_rate_is_a_lever():
    inp = toy_inputs()
    lo = solve(inp.with_(hurdle_rates={"default": 0.035}))
    hi = solve(inp.with_(hurdle_rates={"default": 0.30}))
    assert hi.objective > lo.objective


def test_adoption_ramp_binds():
    inp = toy_inputs()
    techs = dict(inp.technologies)
    import dataclasses
    techs["elec_boiler"] = dataclasses.replace(techs["elec_boiler"],
                                               ramp_limit=0.1)
    capped = solve(inp.with_(technologies=techs,
                             carbon_price_traded=pins({2025: 0.4})))
    per_year = capped.new.query("tech == 'elec_boiler'").groupby("year").units.sum()
    assert (per_year <= 0.5 + 1e-6).all()  # 0.1/yr x 5-yr timestep


def test_window_is_configuration():
    inp = toy_inputs().with_(window=Window(2025, 2035, 5))
    sol = solve(inp)
    assert set(sol.used.year) <= {2025, 2030, 2035}


def test_ensemble_and_spread():
    inp = toy_inputs()
    sols, tidy = run_ensemble(inp, {
        "cheap_elec": lambda i: i.with_(hurdle_rates={"default": 0.05}),
    })
    assert set(sols) == {"central", "cheap_elec"}
    lo, hi = spread(tidy, "gas", 2030)
    assert hi >= lo >= 0


def test_rolling_solve_runs():
    used = rolling_solve(toy_inputs(), window_width=10)
    assert not used.empty
    assert used.query("year == 2025").units.sum() > 0


def test_skill_scoring():
    modelled = pd.DataFrame({"year": [2021, 2022, 2023],
                             "value": [100, 90, 80]})
    outturn = pd.DataFrame({"year": [2021, 2022, 2023],
                            "value": [1000, 950, 850]})
    mape, tbl = indexed_mape(modelled, outturn, 2021)
    assert 0 < mape < 0.1
    assert list(tbl.year) == [2021, 2022, 2023]
