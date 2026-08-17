"""comitpy dashboard - the forecast, visually, plus live levers.

Run:  streamlit run dashboard.py     (pip install -e .[dashboard] first)

Two pages:
- Results: every standard run from results_store.csv (build it with
  `python scripts/build_results_store.py`), sliceable by layer, cluster,
  sector, site and world.
- Levers: move carbon, gas, levies, CCS timing, hurdle or inertia and
  re-solve live against the central forecast.

All model logic lives in comitpy; this file is glue and charts only.
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent
STORE = ROOT / "results_store.csv"
WORLD_RUNS = ["central", "levies_off", "gas_up50", "gas_down30",
              "carbon_x1.5", "carbon_x0.6", "ccs_slip"]

st.set_page_config(page_title="comitpy - UK industrial forecast",
                   layout="wide", initial_sidebar_state="expanded")


@st.cache_data
def load_store(mtime: float) -> pd.DataFrame:
    return pd.read_csv(STORE)


def emissions_total(df, runs):
    e = df[(df.variable == "emissions_ktco2e") & df.run.isin(runs)]
    return e.groupby(["run", "year"], as_index=False).value.sum()


# ---------------------------------------------------------------- Results
def results_page(df):
    st.title("UK industrial forecast - v2 universe")
    st.caption("All UK industry, anchored to the DESNZ territorial total "
               "(~46.5 Mt in 2025). MtCO2e throughout. The hindcast skill "
               "score stays defined on the ETS-verified core.")

    tabs = st.tabs(["National", "Sectors & layers", "Clusters", "Sites",
                    "Fuel", "Pathway"])

    with tabs[0]:
        tot = emissions_total(df, WORLD_RUNS)
        tot["MtCO2e"] = tot.value / 1e3
        band = (tot[tot.run != "central"].groupby("year").MtCO2e
                .agg(["min", "max"]).reset_index())
        central = tot[tot.run == "central"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pd.concat([band.year, band.year[::-1]]),
            y=pd.concat([band["max"], band["min"][::-1]]),
            fill="toself", fillcolor="rgba(44,95,134,0.15)",
            line={"width": 0}, name="ensemble range", hoverinfo="skip"))
        for run in WORLD_RUNS[1:]:
            w = tot[tot.run == run]
            fig.add_trace(go.Scatter(x=w.year, y=w.MtCO2e, name=run,
                                     line={"width": 1}, opacity=0.55))
        fig.add_trace(go.Scatter(x=central.year, y=central.MtCO2e,
                                 name="central", line={"width": 3.5}))
        fig.update_layout(yaxis_title="MtCO2e", legend_title="world",
                          margin={"t": 30})
        st.plotly_chart(fig, width="stretch")
        c1, c2, c3 = st.columns(3)
        e26 = central[central.year == 2026].MtCO2e.iloc[0]
        e36 = central[central.year == 2036].MtCO2e.iloc[0]
        c1.metric("2026 (central)", f"{e26:.1f} Mt")
        c2.metric("2036 (central)", f"{e36:.1f} Mt",
                  f"{e36 - e26:+.1f} Mt", delta_color="inverse")
        band36 = band[band.year == 2036]
        c3.metric("2036 ensemble range",
                  f"{band36['min'].iloc[0]:.1f}-{band36['max'].iloc[0]:.1f} Mt")

    with tabs[1]:
        run = st.selectbox("World", WORLD_RUNS, key="sl_run")
        e = df[(df.variable == "emissions_ktco2e") & (df.run == run)]
        c1, c2 = st.columns(2)
        for col, dim in ((c1, "sector"), (c2, "layer")):
            g = e.groupby([dim, "year"], as_index=False).value.sum()
            g["MtCO2e"] = g.value / 1e3
            fig = px.area(g, x="year", y="MtCO2e", color=dim,
                          title=f"Emissions by {dim}")
            fig.update_layout(margin={"t": 40})
            col.plotly_chart(fig, width="stretch")

    with tabs[2]:
        e = df[(df.variable == "emissions_ktco2e") & (df.run == "central")]
        g = e.groupby(["cluster", "year"], as_index=False).value.sum()
        g["MtCO2e"] = g.value / 1e3
        year = st.select_slider("Year", sorted(g.year.unique()), value=2036)
        snap = (g[g.year == year].sort_values("MtCO2e", ascending=True)
                .tail(10))
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.bar(snap, x="MtCO2e", y="cluster",
                               orientation="h",
                               title=f"Top clusters, {year} (central)"),
                        width="stretch")
        picks = c2.multiselect("Cluster trajectories",
                               sorted(g.cluster.unique()),
                               default=list(snap.cluster.tail(4)))
        c2.plotly_chart(px.line(g[g.cluster.isin(picks)], x="year",
                                y="MtCO2e", color="cluster",
                                title="Cluster trajectories (central)"),
                        width="stretch")

    with tabs[3]:
        e = df[(df.variable == "emissions_ktco2e") & (df.run == "central")]
        c1, c2, c3 = st.columns(3)
        layers = c1.multiselect("Layer", sorted(e.layer.unique()))
        clusters = c2.multiselect("Cluster", sorted(e.cluster.unique()))
        sectors = c3.multiselect("Sector", sorted(e.sector.unique()))
        if layers:
            e = e[e.layer.isin(layers)]
        if clusters:
            e = e[e.cluster.isin(clusters)]
        if sectors:
            e = e[e.sector.isin(sectors)]
        year = st.select_slider("Year", sorted(e.year.unique()), value=2036,
                                key="site_year")
        snap = (e[e.year == year].groupby(["site", "sector", "layer",
                                           "cluster"], as_index=False)
                .value.sum().sort_values("value", ascending=False))
        snap["MtCO2e"] = (snap.value / 1e3).round(3)
        st.dataframe(snap.drop(columns="value").head(25),
                     width="stretch", hide_index=True)
        picks = st.multiselect("Site trajectories",
                               list(snap.site), default=list(snap.site[:4]))
        if picks:
            t = e[e.site.isin(picks)].copy()
            t["MtCO2e"] = t.value / 1e3
            st.plotly_chart(px.line(t, x="year", y="MtCO2e", color="site"),
                            width="stretch")
        st.caption("Site-level figures are meaningful where a committed "
                   "event or dominant economics pins them; elsewhere quote "
                   "the ensemble ranges (SITE-DETAIL.md), not points.")

    with tabs[4]:
        run = st.selectbox("World", WORLD_RUNS, key="fuel_run")
        f = df[(df.variable == "fuel_use_pj") & (df.run == run)]
        g = f.groupby(["detail", "year"], as_index=False).value.sum()
        st.plotly_chart(px.area(g, x="year", y="value", color="detail",
                                labels={"value": "PJ", "detail": "fuel"},
                                title=f"Fuel use, {run}"),
                        width="stretch")

    with tabs[5]:
        runs = ["forecast_2050", "netzero_2050"]
        tot = emissions_total(df, runs)
        tot["MtCO2e"] = tot.value / 1e3
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.line(tot, x="year", y="MtCO2e", color="run",
                                title="Forecast vs net-zero-2050 pathway "
                                      "(2026-2050, biennial)"),
                        width="stretch")
        f = df[(df.variable == "fuel_use_pj") & df.run.isin(runs)
               & (df.year == 2050)]
        g = f.groupby(["run", "detail"], as_index=False).value.sum()
        c2.plotly_chart(px.bar(g, x="detail", y="value", color="run",
                               barmode="group",
                               labels={"value": "PJ", "detail": "fuel"},
                               title="2050 fuel mix"),
                        width="stretch")
        st.caption("The gap between these two lines is what the cap forces "
                   "that economics alone never does - site-by-site detail "
                   "in PATHWAY-SITE-DETAIL.md.")


# ----------------------------------------------------------------- Levers
@st.cache_data(show_spinner=False)
def lever_solve(carbon: float, gas: float, levies: float, slip: int,
                hurdle: float, inertia: float):
    import dataclasses

    from comitpy import Window, solve
    from comitpy.datasets import load_inputs
    from comitpy.worlds import scale_carbon, scale_fuel

    inp = load_inputs(str(ROOT / "datasets"), Window(2026, 2036, 1))
    inp = scale_carbon(inp, carbon)
    inp = scale_fuel(inp, "gas", "wholesale", gas)
    inp = scale_fuel(inp, "electricity", "levies", levies)
    if slip:
        techs = dict(inp.technologies)
        for name in ("cement_kiln_ccs", "gas_boiler_ccs"):
            t = techs[name]
            techs[name] = dataclasses.replace(t, first_year=t.first_year + slip)
        inp = inp.with_(technologies=techs)
    inp = inp.with_(
        hurdle_rates={**inp.hurdle_rates, "default": hurdle},
        usage_inertia_cost=inp.usage_inertia_cost * inertia)
    sol = solve(inp)
    sector_of = {s.name: s.sector for s in inp.sites}
    emis = sol.emissions.copy()
    emis["sector"] = emis.site.map(sector_of)
    by = (emis.groupby(["year", "sector"], as_index=False).ktCO2e.sum())
    return by, float(sol.objective)


def levers_page(df):
    st.title("Levers - re-solve the forecast live")
    st.caption("Central values are the calibrated dataset; every move here "
               "is a what-if on top of it, solved fresh (~10-20 s).")

    with st.form("levers"):
        c1, c2, c3 = st.columns(3)
        carbon = c1.slider("Carbon price x", 0.5, 2.0, 1.0, 0.05)
        gas = c2.slider("Gas wholesale x", 0.5, 2.0, 1.0, 0.05)
        levies = c3.slider("Electricity levies x", 0.0, 1.5, 1.0, 0.05)
        slip = c1.slider("CCS slip (years)", 0, 6, 0, 1)
        hurdle = c2.slider("Hurdle rate (default sectors)", 0.05, 0.35,
                           0.20, 0.01)
        inertia = c3.slider("Usage inertia x", 0.0, 2.0, 1.0, 0.1)
        go_ = st.form_submit_button("Solve", type="primary")

    if not go_:
        st.info("Set the levers and press Solve.")
        return
    try:
        with st.spinner("Solving 2026-2036 annual..."):
            by, obj = lever_solve(carbon, gas, levies, slip, hurdle, inertia)
    except Exception as exc:                     # honest failure, not a blank
        st.error(f"Solve failed: {exc}")
        return

    central = emissions_total(df, ["central"])
    central["MtCO2e"] = central.value / 1e3
    tot = by.groupby("year", as_index=False).ktCO2e.sum()
    tot["MtCO2e"] = tot.ktCO2e / 1e3

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=central.year, y=central.MtCO2e,
                             name="central", line={"dash": "dot"}))
    fig.add_trace(go.Scatter(x=tot.year, y=tot.MtCO2e, name="your levers",
                             line={"width": 3}))
    fig.update_layout(yaxis_title="MtCO2e", margin={"t": 30})
    st.plotly_chart(fig, width="stretch")

    c36 = central[central.year == 2036].MtCO2e.iloc[0]
    y36 = tot[tot.year == 2036].MtCO2e.iloc[0]
    c1, c2 = st.columns(2)
    c1.metric("2036 emissions", f"{y36:.1f} Mt", f"{y36 - c36:+.1f} Mt "
              "vs central", delta_color="inverse")
    c2.metric("PV system cost", f"GBP{obj / 1e3:,.1f}bn")

    by36 = by[by.year == 2036].copy()
    by36["MtCO2e"] = by36.ktCO2e / 1e3
    cen36 = df[(df.variable == "emissions_ktco2e") & (df.run == "central")
               & (df.year == 2036)].groupby("sector").value.sum() / 1e3
    by36["delta_vs_central"] = by36.apply(
        lambda r: r.MtCO2e - cen36.get(r.sector, 0.0), axis=1)
    st.plotly_chart(px.bar(by36, x="sector", y="delta_vs_central",
                           title="2036 sector delta vs central (MtCO2e)"),
                    width="stretch")


# ------------------------------------------------------------------- main
if not STORE.exists():
    st.error("results_store.csv not found - run "
             "`python scripts/build_results_store.py` first.")
    st.stop()

df = load_store(STORE.stat().st_mtime)
page = st.sidebar.radio("Page", ["Results", "Levers"])
st.sidebar.caption("comitpy - COMIT rebuilt: crystal-clear mechanics, "
                   "provenance-tagged inputs. See MECHANICS.md.")
if page == "Results":
    results_page(df)
else:
    levers_page(df)
