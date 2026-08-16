# INPUTS — every lever, generated from the data

Regenerate: `python scripts/describe_inputs.py`.

## `datasets/`

### build_orders.csv — Committed builds (bounds on new capacity).
1 rows; basis mix: official 1

```
                  site tech  year  min_units  max_units                                                                                          source    basis
Port Talbot Steelworks  eaf  2028        3.0        NaN Tata GBP1.25bn EAF under construction since Jul 2025 - operational end-2027 - 3 Mt/yr nameplate official
```

### carbon.csv — Traded/untraded carbon prices and the CBAM phase curve.
11 rows; basis mix: derived 1, judgement 4, market 3, official 2, outturn 1

```
    series  year  value                                                                                                                source     basis
    traded  2025  0.050                                                                                               UKA annual avg ~GBP50/t   outturn
    traded  2026  0.072                                                                  UKA ~GBP72/t H2-26 under EU linkage (Energy Aspects)    market
    traded  2030  0.120                                                                    EUA consensus ~EUR140/t 2030 converged via linkage    market
    traded  2035  0.165                                                                                      EUA consensus ~EUR190-200/t 2035    market
    traded  2050  0.260                                                                                              consensus slope extended judgement
  untraded  2025  0.005                                                          CCL-equivalent ~GBP4-5/t; no non-ETS carbon price legislated  official
  untraded  2050  0.005                                                                                              held flat pending policy judgement
cbam_phase  2026  0.000                                                                                                              pre-CBAM  official
cbam_phase  2027  0.350 UK CBAM live Jan 2027; effective rate = ETS x reduction factor reflecting free allocation (~non-free share initially)   derived
cbam_phase  2032  1.000                                                        free allocation phase-down for CBAM sectors (ramp = judgement) judgement
cbam_phase  2050  1.000                                                                                                                  held judgement
```

### finance.csv — Hurdle rates, discount rate, usage-inertia cost (the calibrated behaviour).
2 rows; basis mix: derived 1, judgement 1

```
 sector  hurdle_rate  discount_rate  usage_inertia_cost                                                                                                                                                                                                                                                                                   source     basis
default         0.20          0.035                36.0 hurdle calibrated vs 2021-25 UK ETS outturn (comit-harness BACKCAST-SKILL.md dip-rebound saturation); discount = Green Book; usage inertia calibrated vs the backcast 2022 dip signature (suppression threshold; LP corner behaviour makes the dip binary - see comit-py backcast notes)   derived
  steel         0.15            NaN                 NaN                                                                                                                                                                                                                      strategic/state-supported investment discounts vs merchant industry judgement
```

### fuel_emissions.csv — Emissions factors per fuel per year (grid decarbonisation lives here).
10 rows; basis mix: derived 1, judgement 3, official 5, outturn 1

```
       fuel  year  value                                                     source     basis
        gas  2025   51.2 DESNZ GHG conversion factors (natural gas net CO2e per PJ)  official
        gas  2050   51.2                            combustion chemistry - constant  official
electricity  2025   35.0  grid intensity 126 g/kWh 2025 outturn (Carbon Brief/NESO)   outturn
electricity  2030   16.7   ~60 g/kWh - Clean Power 2030 adjusted for the 2025 stall  official
electricity  2035    8.3                                          ~30 g/kWh central judgement
electricity  2045    2.8                           ~10 g/kWh deep-decarbonised grid judgement
   hydrogen  2027    8.0              mixed blue/green: upstream CH4 + capture slip   derived
   hydrogen  2050    3.0                                    greening production mix judgement
    biomass  2025    0.0                   biogenic accounting convention (UK GHGI)  official
    biomass  2050    0.0                             biogenic accounting convention  official
```

### fuel_prices.csv — Price stacks per fuel: wholesale/network/levies/margin pins + band multipliers.
25 rows; basis mix: derived 9, judgement 4, market 6, official 4, outturn 2

```
       fuel component   year  value  band  band_factor                                                      source     basis
        gas wholesale 2025.0    3.2   NaN          NaN                                NBP annual avg via DESNZ QEP   outturn
        gas wholesale 2026.0    4.6   NaN          NaN NBP futures Win-26 ~149p/therm (mkt reports 10-13 Aug 2026)    market
        gas wholesale 2027.0    3.5   NaN          NaN                               NBP futures Sum-27 ~95p/therm    market
        gas wholesale 2028.0    2.7   NaN          NaN                               NBP futures Sum-28 ~70p/therm    market
        gas wholesale 2030.0    2.4   NaN          NaN                        DESNZ-central-like long-run LNG cost  official
        gas wholesale 2050.0    2.2   NaN          NaN                               flat-real long-run assumption judgement
        gas   network 2025.0    0.8   NaN          NaN               retail wedge calibrated to QEP industrial avg   derived
        gas    margin 2025.0    0.5   NaN          NaN               retail wedge calibrated to QEP industrial avg   derived
        gas   network    NaN    NaN small          1.5                small-consumer wedge vs QEP size-band spread   derived
        gas    margin    NaN    NaN small          3.0                small-consumer wedge vs QEP size-band spread   derived
electricity wholesale 2025.0   22.8   NaN          NaN                           GB baseload annual avg ~GBP82/MWh   outturn
electricity wholesale 2026.0   30.6   NaN          NaN                        baseload forwards Win-26 ~GBP122/MWh    market
electricity wholesale 2028.0   23.6   NaN          NaN                     baseload forwards easing with gas curve    market
electricity wholesale 2030.0   20.8   NaN          NaN    renewables share lowering wholesale (NESO CP2030-shaped)  official
electricity wholesale 2045.0   18.0   NaN          NaN                                   FES-central-like long run judgement
electricity   network 2025.0   10.0   NaN          NaN          network charges component of QEP industrial retail   derived
electricity    levies 2025.0   12.0   NaN          NaN    policy levies component (RO/CfD/CM) of industrial retail   derived
electricity    margin 2025.0    3.0   NaN          NaN                                   supplier margin component   derived
electricity    levies    NaN    NaN large          0.2                British Industry Supercharger EII exemptions  official
electricity   network    NaN    NaN large          0.4                    Supercharger network charge compensation  official
electricity    margin    NaN    NaN small          2.0                small-consumer wedge vs QEP size-band spread   derived
   hydrogen wholesale 2027.0   11.0   NaN          NaN   HPBM offtaker basis ~gas x1.25 (producers get the strike)   derived
   hydrogen wholesale 2050.0   10.0   NaN          NaN                    HPBM offtaker basis held vs gas long-run judgement
    biomass wholesale 2025.0    8.2   NaN          NaN                                wood chip industrial ~3p/kWh    market
    biomass wholesale 2050.0    8.2   NaN          NaN                                                   flat-real judgement
```

### imports.csv — Import parity prices, embodied carbon, CBAM coverage per commodity.
4 rows; basis mix: judgement 2, market 2

```
commodity  year  price  embodied_ktco2_per_unit  cbam_covered                                                                                                                source     basis
    steel  2026  520.0                   1900.0          True ~GBP520/t delivered import parity; embodied ~1.9 tCO2/t BF-BOF direct (marginal non-EU origin); CBAM sector confirmed    market
    steel  2050  520.0                   1900.0          True                                                                                                        held flat-real judgement
   cement  2026  100.0                    700.0          True                         ~GBP100/t delivered; embodied ~0.7 tCO2/t direct clinker-heavy imports; CBAM sector confirmed    market
   cement  2050  100.0                    700.0          True                                                                                                        held flat-real judgement
```

### sector_output.csv — Sector production indices scaling site demand.
12 rows; basis mix: judgement 7, official 1, outturn 4

```
sector  year  value                                                                                    source     basis
  heat  2025  100.0                                              base year (sites.csv demand is 2025-derived)   outturn
  heat  2026  100.0                                    Make UK/EY 2026 flat-to-+0.9% headline; EI subset lags  official
  heat  2030  100.0                      modest growth (PMI 52.8 Jul-26; AI/defence demand) offset by EI drag judgement
  heat  2036   98.0                                                           long-run EI manufacturing drift judgement
  heat  2050   96.0                                                                                held trend judgement
 steel  2025  100.0                   base year; Port Talbot restart carried by site_overrides not this index   outturn
 steel  2050  100.0 surviving-fleet output flat central (Scunthorpe future undecided - do not encode a guess) judgement
cement  2025  100.0                                                                                 base year   outturn
cement  2026   93.0                 MPA: concrete -9.3% H1-2026 - no sign of recovery - fifth year of malaise   outturn
cement  2028   98.0                                                         slow recovery from the lower base judgement
cement  2030  105.0                                       recovery IF housebuilding targets land (1.5m homes) judgement
cement  2050  105.0                                                                                      held judgement
```

### site_overrides.csv — Site-level demand pins outranking sector trends.
7 rows; basis mix: derived 2, judgement 3, official 2

```
                  site commodity  year  value                                                                                                                                                                     source     basis
Port Talbot Steelworks     steel  2026    0.6                                                                                                            residual downstream operations pre-EAF (2025-emissions-implied)   derived
Port Talbot Steelworks     steel  2027    0.6                                                                                                                                                 EAF commissioning end-2027  official
Port Talbot Steelworks     steel  2028    3.0                                                                                                EAF nameplate 3 Mt/yr from 2028 (Tata GBP1.25bn project under construction)  official
Port Talbot Steelworks     steel  2050    3.0                                                                                                                                                          held at nameplate judgement
        dispersed_heat      heat  2026   45.1                                                                                                                                                        base (2025-derived)   derived
        dispersed_heat      heat  2027   43.2 announced 2026 closures within the aggregate: AGC Thornton Cleveleys (end-2026) + Nippon Electric Glass Wigan + JDE Banbury + Union Electric Gateshead ~ -1.9 PJ estimated judgement
        dispersed_heat      heat  2050   43.2                                                                                                                                                                       held judgement
```

### sites.csv — The site universe: who, where (band), how big, incumbent kit, inertia factor.
102 rows; basis mix: derived 102
(large file — see the CSV; columns: site, sector, band, traded, commodity, demand_pj, incumbent_tech, start_capacity, inertia_factor, source, retrieved, basis)

### technologies.csv — The technology roster: costs, lifetimes, fuel intensities, first years, ramps.
10 rows; basis mix: derived 3, judgement 5, official 2

```
     technology sector output  capex  opex  lifetime  availability  capture_rate  process_emissions  first_year  ramp_limit        fuel  fuel_use                                                        source     basis
     gas_boiler   heat   heat    8.0  0.30        20          0.90          0.00                0.0           0         NaN         gas      1.11                  industrial boiler ~90% eff; capex indicative judgement
    elec_boiler   heat   heat    9.0  0.30        20          0.90          0.00                0.0           0         NaN electricity      1.02                   electrode boiler ~98% eff; capex indicative judgement
      heat_pump   heat   heat   25.0  0.60        18          0.90          0.00                0.0        2026         3.0 electricity      0.35 industrial HP COP ~2.9; capex indicative; ramp = supply chain judgement
 biomass_boiler   heat   heat   14.0  0.50        20          0.85          0.00                0.0           0         1.5     biomass      1.18   biomass boiler ~85% eff; ramp = sustainable feedstock build judgement
hydrogen_boiler   heat   heat    9.5  0.35        20          0.90          0.00                0.0        2027         2.0    hydrogen      1.15         H2-ready boiler; first year = Merseyside HAR timeline   derived
 gas_boiler_ccs   heat   heat   30.0  1.20        20          0.85          0.90                0.0        2028         1.0         gas      1.25 post-combustion capture on gas heat; first year = Track-1 ops judgement
            bof  steel  steel  400.0 12.00        25          0.90          0.00             1700.0           0         NaN         gas      3.00             BF-BOF route; process EF ~1.7 tCO2/t + fuel proxy   derived
            eaf  steel  steel  417.0 10.00        25          0.90          0.00               50.0        2027         NaN electricity      2.20               Port Talbot EAF GBP1.25bn / 3 Mt-yr; ~0.6 MWh/t  official
    cement_kiln cement cement  150.0  5.00        30          0.90          0.00              520.0           0         NaN         gas      3.50                  dry kiln; calcination ~520 ktCO2e/Mt clinker  official
cement_kiln_ccs cement cement  375.0 12.00        30          0.85          0.95              520.0        2028         0.5         gas      3.90     amine capture (Padeswood-class); first year = Track-1 ops   derived
```

## `datasets_backcast/`

### carbon.csv — Traded/untraded carbon prices and the CBAM phase curve.
8 rows; basis mix: judgement 1, official 2, outturn 5

```
  series  year  value                         source     basis
  traded  2021  0.053            UKA annual averages   outturn
  traded  2022  0.078            UKA annual averages   outturn
  traded  2023  0.058            UKA annual averages   outturn
  traded  2024  0.037            UKA annual averages   outturn
  traded  2025  0.050            UKA annual averages   outturn
  traded  2029  0.055 held ~flat beyond scored years judgement
untraded  2021  0.004                 CCL-equivalent  official
untraded  2029  0.004                      held flat  official
```

### committed_events.csv — Committed closures (demand zeroed from year).
3 rows; basis mix: official 3

```
                  site  from_year                                                                     source    basis
Port Talbot Steelworks       2025 Tata BF/BOS closed Sep-Oct 2024; EAF operational end-2027 (outside window) official
  Grangemouth Refining       2025            Petroineos ceased refining Apr 2025; import terminal thereafter official
  Lindsey Oil Refinery       2025       Prax insolvency Jun 2025; refining ceased, mothballed by Phillips 66 official
```

### finance.csv — Hurdle rates, discount rate, usage-inertia cost (the calibrated behaviour).
2 rows; basis mix: derived 1, judgement 1

```
 sector  hurdle_rate  discount_rate  usage_inertia_cost                                                                                                                                                                                                                                                                                   source     basis
default         0.20          0.035                36.0 hurdle calibrated vs 2021-25 UK ETS outturn (comit-harness BACKCAST-SKILL.md dip-rebound saturation); discount = Green Book; usage inertia calibrated vs the backcast 2022 dip signature (suppression threshold; LP corner behaviour makes the dip binary - see comit-py backcast notes)   derived
  steel         0.15            NaN                 NaN                                                                                                                                                                                                                      strategic/state-supported investment discounts vs merchant industry judgement
```

### fuel_emissions.csv — Emissions factors per fuel per year (grid decarbonisation lives here).
12 rows; basis mix: derived 5, official 4, outturn 3

```
       fuel  year  value                                             source    basis
        gas  2021   51.2                           DESNZ conversion factors official
        gas  2029   51.2                                           constant official
electricity  2021   54.2 grid intensity outturn (g/kWh x 0.2778); 21-22 est  derived
electricity  2022   50.6 grid intensity outturn (g/kWh x 0.2778); 21-22 est  derived
electricity  2023   47.5 grid intensity outturn (g/kWh x 0.2778); 21-22 est  outturn
electricity  2024   34.4 grid intensity outturn (g/kWh x 0.2778); 21-22 est  outturn
electricity  2025   35.0 grid intensity outturn (g/kWh x 0.2778); 21-22 est  outturn
electricity  2029   35.0 grid intensity outturn (g/kWh x 0.2778); 21-22 est  derived
    biomass  2021    0.0                                biogenic convention official
    biomass  2029    0.0                                biogenic convention official
   hydrogen  2021    8.0                        unused pre-2027 (tech gate)  derived
   hydrogen  2029    8.0                                    unused pre-2027  derived
```

### fuel_prices.csv — Price stacks per fuel: wholesale/network/levies/margin pins + band multipliers.
24 rows; basis mix: derived 10, judgement 2, market 1, official 1, outturn 10

```
       fuel component   year  value  band  band_factor                                       source     basis
        gas wholesale 2021.0   5.37   NaN          NaN   DESNZ QEP industrial avg minus fixed wedge   outturn
        gas wholesale 2022.0  15.92   NaN          NaN   DESNZ QEP industrial avg minus fixed wedge   outturn
        gas wholesale 2023.0  12.31   NaN          NaN   DESNZ QEP industrial avg minus fixed wedge   outturn
        gas wholesale 2024.0   9.53   NaN          NaN   DESNZ QEP industrial avg minus fixed wedge   outturn
        gas wholesale 2025.0   8.98   NaN          NaN   DESNZ QEP industrial avg minus fixed wedge   outturn
        gas wholesale 2029.0   8.98   NaN          NaN                held flat beyond scored years judgement
electricity wholesale 2021.0  15.00   NaN          NaN   DESNZ QEP industrial avg minus fixed wedge   outturn
electricity wholesale 2022.0  33.61   NaN          NaN   DESNZ QEP industrial avg minus fixed wedge   outturn
electricity wholesale 2023.0  42.22   NaN          NaN   DESNZ QEP industrial avg minus fixed wedge   outturn
electricity wholesale 2024.0  26.67   NaN          NaN   DESNZ QEP industrial avg minus fixed wedge   outturn
electricity wholesale 2025.0  23.06   NaN          NaN   DESNZ QEP industrial avg minus fixed wedge   outturn
electricity wholesale 2029.0  23.06   NaN          NaN                held flat beyond scored years judgement
        gas   network 2021.0   0.80   NaN          NaN                    wedge as forward datasets   derived
        gas    margin 2021.0   0.50   NaN          NaN                    wedge as forward datasets   derived
        gas   network    NaN    NaN small          1.5                         QEP size-band spread   derived
        gas    margin    NaN    NaN small          3.0                         QEP size-band spread   derived
electricity   network 2021.0  10.00   NaN          NaN                    wedge as forward datasets   derived
electricity    levies 2021.0  12.00   NaN          NaN                    wedge as forward datasets   derived
electricity    margin 2021.0   3.00   NaN          NaN                    wedge as forward datasets   derived
electricity    levies    NaN    NaN large          0.2                               EII exemptions  official
electricity   network    NaN    NaN large          0.4  Supercharger (post-2025; approximation pre)   derived
electricity    margin    NaN    NaN small          2.0                         QEP size-band spread   derived
    biomass wholesale 2021.0   8.20   NaN          NaN                            wood chip ~3p/kWh    market
   hydrogen wholesale 2021.0  11.00   NaN          NaN unused pre-2027 (technology first_year gate)   derived
```

### imports.csv — Import parity prices, embodied carbon, CBAM coverage per commodity.
2 rows; basis mix: judgement 2

```
commodity  year  price  embodied_ktco2_per_unit  cbam_covered                             source     basis
    steel  2021  500.0                   1900.0          True historical import parity ~GBP500/t judgement
   cement  2021   90.0                    700.0          True  historical import parity ~GBP90/t judgement
```

### outturn.csv — The scoring truth for the hindcast (UK ETS verified).
5 rows; basis mix: outturn 5

```
 year   value                                                         source   basis
 2021 42379.1 UK ETS compliance report 2021-2025 (registry, pub 22 Jun 2026) outturn
 2022 40593.0 UK ETS compliance report 2021-2025 (registry, pub 22 Jun 2026) outturn
 2023 37730.5 UK ETS compliance report 2021-2025 (registry, pub 22 Jun 2026) outturn
 2024 34345.8 UK ETS compliance report 2021-2025 (registry, pub 22 Jun 2026) outturn
 2025 29323.5 UK ETS compliance report 2021-2025 (registry, pub 22 Jun 2026) outturn
```

### sector_output.csv — Sector production indices scaling site demand.
15 rows; basis mix: derived 5, judgement 3, outturn 7

```
sector  year  value                                                   source     basis
  heat  2021  100.0                                                base year   outturn
  heat  2022   96.0            ONS IoP manufacturing -3.4% 2022, EI-weighted   derived
  heat  2023   93.0          ONS IoP -0.3% 2023 but chemicals/EI fell harder   derived
  heat  2024   92.0               EI manufacturing broadly flat-to-down 2024   derived
  heat  2029   92.0                                 held beyond scored years judgement
 steel  2021  100.0                               UK crude steel 7.2 Mt 2021   outturn
 steel  2022   85.0                                              6.1 Mt 2022   outturn
 steel  2023   78.0                                              5.6 Mt 2023   outturn
 steel  2024   78.0 held: PT closure event carries 2024-25 (no double count)   derived
 steel  2029   78.0                                 held beyond scored years judgement
cement  2021  100.0                                   GB cement ~9.3 Mt 2021   outturn
cement  2022   90.0                                        8.4 Mt 2022 (MPA)   outturn
cement  2023   84.0                                    construction slowdown   derived
cement  2024   78.0                          7.3 Mt 2024 - 75-year low (MPA)   outturn
cement  2029   77.0                                 held beyond scored years judgement
```

### sites.csv — The site universe: who, where (band), how big, incumbent kit, inertia factor.
102 rows; basis mix: derived 102
(large file — see the CSV; columns: site, sector, band, traded, commodity, demand_pj, incumbent_tech, start_capacity, inertia_factor, source, retrieved, basis)

### technologies.csv — The technology roster: costs, lifetimes, fuel intensities, first years, ramps.
10 rows; basis mix: derived 3, judgement 5, official 2

```
     technology sector output  capex  opex  lifetime  availability  capture_rate  process_emissions  first_year  ramp_limit        fuel  fuel_use                                                        source     basis
     gas_boiler   heat   heat    8.0  0.30        20          0.90          0.00                0.0           0         NaN         gas      1.11                  industrial boiler ~90% eff; capex indicative judgement
    elec_boiler   heat   heat    9.0  0.30        20          0.90          0.00                0.0           0         NaN electricity      1.02                   electrode boiler ~98% eff; capex indicative judgement
      heat_pump   heat   heat   25.0  0.60        18          0.90          0.00                0.0        2026         3.0 electricity      0.35 industrial HP COP ~2.9; capex indicative; ramp = supply chain judgement
 biomass_boiler   heat   heat   14.0  0.50        20          0.85          0.00                0.0           0         1.5     biomass      1.18   biomass boiler ~85% eff; ramp = sustainable feedstock build judgement
hydrogen_boiler   heat   heat    9.5  0.35        20          0.90          0.00                0.0        2027         2.0    hydrogen      1.15         H2-ready boiler; first year = Merseyside HAR timeline   derived
 gas_boiler_ccs   heat   heat   30.0  1.20        20          0.85          0.90                0.0        2028         1.0         gas      1.25 post-combustion capture on gas heat; first year = Track-1 ops judgement
            bof  steel  steel  400.0 12.00        25          0.90          0.00             1700.0           0         NaN         gas      3.00             BF-BOF route; process EF ~1.7 tCO2/t + fuel proxy   derived
            eaf  steel  steel  417.0 10.00        25          0.90          0.00               50.0        2027         NaN electricity      2.20               Port Talbot EAF GBP1.25bn / 3 Mt-yr; ~0.6 MWh/t  official
    cement_kiln cement cement  150.0  5.00        30          0.90          0.00              520.0           0         NaN         gas      3.50                  dry kiln; calcination ~520 ktCO2e/Mt clinker  official
cement_kiln_ccs cement cement  375.0 12.00        30          0.85          0.95              520.0        2028         0.5         gas      3.90     amine capture (Padeswood-class); first year = Track-1 ops   derived
```
