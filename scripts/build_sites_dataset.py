"""Generate datasets/sites.csv from the real UK ETS compliance data (the
harness's verified 2025 site picture) - not from COMIT's template.

v0 method, every derivation tagged:
- top installations by 2025 verified emissions, industrial NACE only,
  plus per-sector aggregates for the tail;
- sector mapping: iron & steel -> steel, cement -> cement, else -> heat
  (generic industrial heat service);
- band by size (large >500 kt, mid >50 kt, else small);
- demand: v0 emissions-implied activity (gas-equivalent PJ at 51.2
  ktCO2e/PJ x 0.9 boiler efficiency for heat; Mt via sector emissions
  intensity for steel/cement). Replace with real production data as the
  first dataset upgrade.
"""
import csv
from collections import defaultdict

import openpyxl

ETS = r"D:\comit-harness\data\uk_ets_compliance_2021_2025.xlsx"
CW = r"D:\comit-harness\data\ets_naei_crosswalk.csv"
OUT = r"D:\comit-py\datasets\sites.csv"

SRC = "UK ETS compliance report 2021-2025 (registry, pub 22 Jun 2026) via comit-harness"
RET = "2026-08-16"

wb = openpyxl.load_workbook(ETS, read_only=True)
rows = list(wb["Data"].iter_rows(values_only=True))
hdr = {h: i for i, h in enumerate(rows[0])}


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# sector by NACE (registry) - crosswalk sectors would refine this further
def sector_of(nace, desc):
    d = (desc or "").lower()
    if nace.startswith("241") or "basic iron and steel" in d:
        return "steel"
    if nace.startswith("2351") or "cement" in d:
        return "cement"
    return "heat"


# cluster geography: ETS permit -> harness crosswalk -> NAEI plant ->
# cluster_location. Coverage follows the crosswalk (~91% of traded
# emissions); unmatched sites are honestly "Unmapped".
import openpyxl as _oxl

cw = {}
with open(CW, encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        for part in row["permits"].split(";"):
            if "x" in part:
                permit, frac = part.rsplit("x", 1)
                if permit not in cw or float(frac) > cw[permit][1]:
                    cw[permit] = (row["plant_id"], float(frac))

_naei = _oxl.load_workbook(
    r"D:\comit-harness\comit\data_template_archive"
    r"\comit_input_1_4_0_public_updated.xlsx", read_only=True)
_nr = list(_naei["NAEI_df_clean_2023_revised"].iter_rows(values_only=True))
_hi = next(i for i, r in enumerate(_nr) if r and "PlantID" in [str(c) for c in r])
_nh = {h: i for i, h in enumerate(_nr[_hi])}
plant_cluster = {str(r[_nh["PlantID"]]): str(r[_nh["cluster_location"]])
                 for r in _nr[_hi + 1:] if r and r[_nh["PlantID"]]}


def cluster_of(permit):
    hit = cw.get(str(permit))
    if not hit:
        return "Unmapped"
    c = plant_cluster.get(hit[0], "Unmapped")
    return "Dispersed" if c == "Not in cluster" else c


ets = []
for r in rows[1:]:
    if r[hdr["Account type"]] != "OPERATOR_HOLDING_ACCOUNT":
        continue
    nace = str(r[hdr["NACE"]] or "")
    desc = str(r[hdr["NACE Description"]] or "")
    if nace.startswith("35") or "electricity" in desc.lower():
        continue  # power sector out of scope
    if "extraction" in desc.lower():
        continue  # upstream oil & gas out of scope
    e25 = num(r[hdr["Recorded emissions 2025"]])
    ly = num(r[hdr["Last Year of Operation"]])
    if e25 is None or e25 < 1000 or (ly and ly <= 2025):
        continue
    ets.append({
        "name": (r[hdr["Installation name"]] or r[hdr["Account Holder Name"]]),
        "sector": sector_of(nace, desc),
        "e25_kt": e25 / 1e3,
        "cluster": cluster_of(r[hdr["Permit ID or Monitoring plan ID"]]),
    })

ets.sort(key=lambda e: -e["e25_kt"])
top, tail = ets[:100], ets[100:]

INTENSITY = {"steel": 1900.0, "cement": 750.0}   # ktCO2e per Mt output, v0


def demand_and_tech(sector, e25_kt):
    if sector == "steel":
        return e25_kt / INTENSITY["steel"], "bof"
    if sector == "cement":
        return e25_kt / INTENSITY["cement"], "cement_kiln"
    return e25_kt / 51.2 * 0.9, "gas_boiler"


# per-site inertia factors: band base (larger operators have lower switching
# disruption) x a size-rank gradient within band (0.7 largest .. 1.3 smallest)
# - deterministic heterogeneity smoothing the aggregate inertia response
BAND_BASE = {"large": 0.8, "mid": 1.0, "small": 1.3}


def inertia_factors(entries, size_key):
    by_band = {}
    for e in entries:
        kt = e[size_key]
        band = "large" if kt > 500 else ("mid" if kt > 50 else "small")
        by_band.setdefault(band, []).append(e)
    factors = {}
    for band, group in by_band.items():
        group.sort(key=lambda x: -x[size_key])
        n = len(group)
        for i, e in enumerate(group):
            grad = 0.7 + 0.6 * (i / (n - 1) if n > 1 else 0.5)
            factors[e["name"]] = round(BAND_BASE[band] * grad, 3)
    return factors


factors = inertia_factors(top, "e25_kt")

out = []
for e in top:
    band = "large" if e["e25_kt"] > 500 else ("mid" if e["e25_kt"] > 50 else "small")
    d, tech = demand_and_tech(e["sector"], e["e25_kt"])
    commodity = e["sector"] if e["sector"] in ("steel", "cement") else "heat"
    out.append([e["name"], e["sector"], band, True, commodity,
                round(d, 4), tech, round(d / 0.9, 4), factors[e["name"]],
                e["cluster"], SRC, RET, "derived"])

tail_by_sector = defaultdict(float)
for e in tail:
    tail_by_sector[e["sector"]] += e["e25_kt"]
for sector, kt in sorted(tail_by_sector.items()):
    d, tech = demand_and_tech(sector, kt)
    commodity = sector if sector in ("steel", "cement") else "heat"
    out.append([f"dispersed_{sector}", sector, "small", False, commodity,
                round(d, 4), tech, round(d / 0.9, 4), 1.3, "Dispersed",
                SRC + " (aggregate of sub-100 installations)", RET, "derived"])

with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["site", "sector", "band", "traded", "commodity", "demand_pj",
                "incumbent_tech", "start_capacity", "inertia_factor",
                "cluster", "source", "retrieved", "basis"])
    w.writerows(out)
print(f"wrote {OUT}: {len(out)} sites "
      f"({len(top)} named + {len(tail_by_sector)} dispersed aggregates)")
