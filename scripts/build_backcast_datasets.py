"""Generate datasets_backcast/: historical 2021-2025 inputs for the skill
gate, plus the outturn series over exactly the same site universe.

Sites are weighted by 2021 verified emissions (standing in 2021); the
outturn per year is the sum of those same installations' recorded emissions
2021-2025 - so modelled and outturn universes match by construction, the
clean version of what the harness did via the crosswalk.
"""
import csv
import shutil
from collections import defaultdict

import openpyxl

ETS = r"D:\comit-harness\data\uk_ets_compliance_2021_2025.xlsx"
OUT = r"D:\comit-py\datasets_backcast"
SRC = "UK ETS compliance report 2021-2025 (registry, pub 22 Jun 2026)"
RET = "2026-08-16"

wb = openpyxl.load_workbook(ETS, read_only=True)
rows = list(wb["Data"].iter_rows(values_only=True))
hdr = {h: i for i, h in enumerate(rows[0])}


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def sector_of(nace, desc):
    d = (desc or "").lower()
    if nace.startswith("241") or "basic iron and steel" in d:
        return "steel"
    if nace.startswith("2351") or "cement" in d:
        return "cement"
    return "heat"


ets = []
for r in rows[1:]:
    if r[hdr["Account type"]] != "OPERATOR_HOLDING_ACCOUNT":
        continue
    nace = str(r[hdr["NACE"]] or "")
    desc = str(r[hdr["NACE Description"]] or "")
    if nace.startswith("35") or "electricity" in desc.lower() \
            or "extraction" in desc.lower():
        continue
    e = {y: num(r[hdr[f"Recorded emissions {y}"]]) for y in range(2021, 2026)}
    if e[2021] is None or e[2021] < 1000:
        continue
    if any(v is None for v in e.values()):
        continue  # opt-outs leave the outturn series - exclude both sides
    ets.append({"name": (r[hdr["Installation name"]]
                         or r[hdr["Account Holder Name"]]),
                "sector": sector_of(nace, desc), "e": e})

ets.sort(key=lambda x: -x["e"][2021])
top, tail = ets[:100], ets[100:]

INTENSITY = {"steel": 1900.0, "cement": 750.0}


def demand_and_tech(sector, e21_kt):
    if sector == "steel":
        return e21_kt / INTENSITY["steel"], "bof"
    if sector == "cement":
        return e21_kt / INTENSITY["cement"], "cement_kiln"
    return e21_kt / 51.2 * 0.9, "gas_boiler"


site_rows = []
for x in top:
    kt = x["e"][2021] / 1e3
    band = "large" if kt > 500 else ("mid" if kt > 50 else "small")
    d, tech = demand_and_tech(x["sector"], kt)
    commodity = x["sector"] if x["sector"] in ("steel", "cement") else "heat"
    site_rows.append([x["name"], x["sector"], band, True, commodity,
                      round(d, 4), tech, round(d / 0.9, 4),
                      SRC + " (2021 weights)", RET, "derived"])
tail_by_sector = defaultdict(float)
for x in tail:
    tail_by_sector[x["sector"]] += x["e"][2021] / 1e3
for sector, kt in sorted(tail_by_sector.items()):
    d, tech = demand_and_tech(sector, kt)
    commodity = sector if sector in ("steel", "cement") else "heat"
    site_rows.append([f"dispersed_{sector}", sector, "small", False, commodity,
                      round(d, 4), tech, round(d / 0.9, 4),
                      SRC + " (tail aggregate, 2021 weights)", RET, "derived"])

outturn = {y: sum(x["e"][y] for x in top) / 1e3
           + sum(x["e"][y] for x in tail) / 1e3 for y in range(2021, 2026)}

import os
os.makedirs(OUT, exist_ok=True)

with open(f"{OUT}/sites.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["site", "sector", "band", "traded", "commodity", "demand_pj",
                "incumbent_tech", "start_capacity", "source", "retrieved",
                "basis"])
    w.writerows(site_rows)

with open(f"{OUT}/outturn.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["year", "value", "source", "retrieved", "basis"])
    for y, v in outturn.items():
        w.writerow([y, round(v, 1), SRC, RET, "outturn"])

# historical prices (DESNZ QEP annual industrial averages; harness
# lib_real_prices.R values), decomposed with the same wedge structure as the
# forward datasets so band factors carry over
hist = {
    "gas":  {2021: 2.4, 2022: 6.2, 2023: 4.9, 2024: 3.9, 2025: 3.7},
    "electricity": {2021: 14.4, 2022: 21.1, 2023: 24.2, 2024: 18.6, 2025: 17.3},
}
WEDGE = {"gas": 1.3, "electricity": 25.0}
with open(f"{OUT}/fuel_prices.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["fuel", "component", "year", "value", "band", "band_factor",
                "source", "retrieved", "basis"])
    for fuel, series in hist.items():
        for y, p in series.items():
            w.writerow([fuel, "wholesale", y,
                        round(p * 2.7778 - WEDGE[fuel], 2), "", "",
                        "DESNZ QEP industrial avg minus fixed wedge", RET,
                        "outturn"])
        w.writerow([fuel, "wholesale", 2029,
                    round(series[2025] * 2.7778 - WEDGE[fuel], 2), "", "",
                    "held flat beyond scored years", RET, "judgement"])
    w.writerow(["gas", "network", 2021, 0.8, "", "",
                "wedge as forward datasets", RET, "derived"])
    w.writerow(["gas", "margin", 2021, 0.5, "", "",
                "wedge as forward datasets", RET, "derived"])
    w.writerow(["gas", "network", "", "", "small", 1.5,
                "QEP size-band spread", RET, "derived"])
    w.writerow(["gas", "margin", "", "", "small", 3.0,
                "QEP size-band spread", RET, "derived"])
    w.writerow(["electricity", "network", 2021, 10.0, "", "",
                "wedge as forward datasets", RET, "derived"])
    w.writerow(["electricity", "levies", 2021, 12.0, "", "",
                "wedge as forward datasets", RET, "derived"])
    w.writerow(["electricity", "margin", 2021, 3.0, "", "",
                "wedge as forward datasets", RET, "derived"])
    w.writerow(["electricity", "levies", "", "", "large", 0.2,
                "EII exemptions", RET, "official"])
    w.writerow(["electricity", "network", "", "", "large", 0.4,
                "Supercharger (post-2025; approximation pre)", RET, "derived"])
    w.writerow(["electricity", "margin", "", "", "small", 2.0,
                "QEP size-band spread", RET, "derived"])
    w.writerow(["biomass", "wholesale", 2021, 8.2, "", "",
                "wood chip ~3p/kWh", RET, "market"])
    w.writerow(["hydrogen", "wholesale", 2021, 11.0, "", "",
                "unused pre-2027 (technology first_year gate)", RET, "derived"])

with open(f"{OUT}/carbon.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["series", "year", "value", "source", "retrieved", "basis"])
    for y, p in {2021: 53, 2022: 78, 2023: 58, 2024: 37, 2025: 50}.items():
        w.writerow(["traded", y, p / 1000, "UKA annual averages", RET, "outturn"])
    w.writerow(["traded", 2029, 0.055, "held ~flat beyond scored years", RET,
                "judgement"])
    w.writerow(["untraded", 2021, 0.004, "CCL-equivalent", RET, "official"])
    w.writerow(["untraded", 2029, 0.004, "held flat", RET, "official"])

with open(f"{OUT}/fuel_emissions.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["fuel", "year", "value", "source", "retrieved", "basis"])
    w.writerow(["gas", 2021, 51.2, "DESNZ conversion factors", RET, "official"])
    w.writerow(["gas", 2029, 51.2, "constant", RET, "official"])
    for y, g in {2021: 54.2, 2022: 50.6, 2023: 47.5, 2024: 34.4, 2025: 35.0,
                 2029: 35.0}.items():
        w.writerow(["electricity", y, g,
                    "grid intensity outturn (g/kWh x 0.2778); 21-22 est", RET,
                    "outturn" if y in (2023, 2024, 2025) else "derived"])
    w.writerow(["biomass", 2021, 0.0, "biogenic convention", RET, "official"])
    w.writerow(["biomass", 2029, 0.0, "biogenic convention", RET, "official"])
    w.writerow(["hydrogen", 2021, 8.0, "unused pre-2027 (tech gate)", RET,
                "derived"])
    w.writerow(["hydrogen", 2029, 8.0, "unused pre-2027", RET, "derived"])

for f in ("technologies.csv", "finance.csv"):
    shutil.copy(rf"D:\comit-py\datasets\{f}", f"{OUT}/{f}")

print(f"wrote {OUT}: {len(site_rows)} sites; outturn 2021-2025 =",
      {y: round(v / 1e3, 1) for y, v in outturn.items()}, "MtCO2e")
