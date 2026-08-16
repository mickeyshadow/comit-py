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
    ly = num(r[hdr["Last Year of Operation"]])
    ets.append({"name": (r[hdr["Installation name"]]
                         or r[hdr["Account Holder Name"]]),
                "sector": sector_of(nace, desc), "e": e,
                "last_year": int(ly) if ly else None})

ets.sort(key=lambda x: -x["e"][2021])
top, tail = ets[:100], ets[100:]

INTENSITY = {"steel": 1900.0, "cement": 750.0}


def demand_and_tech(sector, e21_kt):
    if sector == "steel":
        return e21_kt / INTENSITY["steel"], "bof"
    if sector == "cement":
        return e21_kt / INTENSITY["cement"], "cement_kiln"
    return e21_kt / 51.2 * 0.9, "gas_boiler"


# per-site inertia factors: band base x size-rank gradient (same rule and
# provenance as the forward generator - deterministic heterogeneity)
BAND_BASE = {"large": 0.8, "mid": 1.0, "small": 1.3}
by_band: dict[str, list] = {}
for x in top:
    kt = x["e"][2021] / 1e3
    band = "large" if kt > 500 else ("mid" if kt > 50 else "small")
    by_band.setdefault(band, []).append((kt, x["name"]))
factors = {}
for band, group in by_band.items():
    group.sort(key=lambda p: -p[0])
    n = len(group)
    for i, (_, name) in enumerate(group):
        grad = 0.7 + 0.6 * (i / (n - 1) if n > 1 else 0.5)
        factors[name] = round(BAND_BASE[band] * grad, 3)

site_rows = []
for x in top:
    kt = x["e"][2021] / 1e3
    band = "large" if kt > 500 else ("mid" if kt > 50 else "small")
    d, tech = demand_and_tech(x["sector"], kt)
    commodity = x["sector"] if x["sector"] in ("steel", "cement") else "heat"
    site_rows.append([x["name"], x["sector"], band, True, commodity,
                      round(d, 4), tech, round(d / 0.9, 4), factors[x["name"]],
                      SRC + " (2021 weights)", RET, "derived"])
tail_by_sector = defaultdict(float)
for x in tail:
    tail_by_sector[x["sector"]] += x["e"][2021] / 1e3
for sector, kt in sorted(tail_by_sector.items()):
    d, tech = demand_and_tech(sector, kt)
    commodity = sector if sector in ("steel", "cement") else "heat"
    site_rows.append([f"dispersed_{sector}", sector, "small", False, commodity,
                      round(d, 4), tech, round(d / 0.9, 4), 1.3,
                      SRC + " (tail aggregate, 2021 weights)", RET, "derived"])

outturn = {y: sum(x["e"][y] for x in top) / 1e3
           + sum(x["e"][y] for x in tail) / 1e3 for y in range(2021, 2026)}

import os
os.makedirs(OUT, exist_ok=True)

with open(f"{OUT}/sites.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["site", "sector", "band", "traded", "commodity", "demand_pj",
                "incumbent_tech", "start_capacity", "inertia_factor",
                "source", "retrieved", "basis"])
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

# committed events: registry-corroborated closures (left the scheme AND
# emissions collapsed - the harness's rule separating closure from opt-out)
# plus the strategic facts with their own sources. NOTE: a hindcast fed
# these measures CONDITIONAL skill - the behavioural ceiling with events
# known - not what a 2021-vintage forecast would have achieved.
included = {x["name"] for x in top}
events = []
for x in top:
    ly = x["last_year"]
    if ly and ly < 2025:
        post = [x["e"][y] for y in range(ly + 1, 2026)]
        if post and max(post) < 0.05 * x["e"][2021]:
            events.append([x["name"], ly + 1,
                           SRC + " (Last Year of Operation, corroborated by "
                           "emissions collapse)", RET, "outturn"])
MANUAL = [
    ("Port Talbot Steelworks", 2025,
     "Tata BF/BOS closed Sep-Oct 2024; EAF operational end-2027 (outside window)"),
    ("Grangemouth Refining", 2025,
     "Petroineos ceased refining Apr 2025; import terminal thereafter"),
    ("Lindsey Oil Refinery", 2025,
     "Prax insolvency Jun 2025; refining ceased, mothballed by Phillips 66"),
]
auto_named = {e[0] for e in events}
for name, year, why in MANUAL:
    if name not in included:
        print(f"  WARNING: manual event site not in universe: {name}")
        continue
    if name in auto_named:
        continue
    events.append([name, year, why, RET, "official"])

# sector output indices (2021=100): the surviving-sites production decline.
# Steel is held at its pre-closure level from 2024 so the Port Talbot
# closure event is not double-counted - the index carries the market
# decline, the event carries the boardroom decision.
SECTOR_OUTPUT = [
    ("heat", 2021, 100.0, "base year", "outturn"),
    ("heat", 2022, 96.0, "ONS IoP manufacturing -3.4% 2022, EI-weighted", "derived"),
    ("heat", 2023, 93.0, "ONS IoP -0.3% 2023 but chemicals/EI fell harder", "derived"),
    ("heat", 2024, 92.0, "EI manufacturing broadly flat-to-down 2024", "derived"),
    ("heat", 2029, 92.0, "held beyond scored years", "judgement"),
    ("steel", 2021, 100.0, "UK crude steel 7.2 Mt 2021", "outturn"),
    ("steel", 2022, 85.0, "6.1 Mt 2022", "outturn"),
    ("steel", 2023, 78.0, "5.6 Mt 2023", "outturn"),
    ("steel", 2024, 78.0, "held: PT closure event carries 2024-25 (no double count)", "derived"),
    ("steel", 2029, 78.0, "held beyond scored years", "judgement"),
    ("cement", 2021, 100.0, "GB cement ~9.3 Mt 2021", "outturn"),
    ("cement", 2022, 90.0, "8.4 Mt 2022 (MPA)", "outturn"),
    ("cement", 2023, 84.0, "construction slowdown", "derived"),
    ("cement", 2024, 78.0, "7.3 Mt 2024 - 75-year low (MPA)", "outturn"),
    ("cement", 2029, 77.0, "held beyond scored years", "judgement"),
]
with open(f"{OUT}/sector_output.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["sector", "year", "value", "source", "retrieved", "basis"])
    for sector, y, v, src2, basis in SECTOR_OUTPUT:
        w.writerow([sector, y, v, src2, RET, basis])

with open(f"{OUT}/committed_events.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["site", "from_year", "source", "retrieved", "basis"])
    w.writerows(events)
print(f"committed events: {len(events)} closures encoded")

print(f"wrote {OUT}: {len(site_rows)} sites; outturn 2021-2025 =",
      {y: round(v / 1e3, 1) for y, v in outturn.items()}, "MtCO2e")
