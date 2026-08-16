"""Generate INPUTS.md: every lever in the model, from the data itself.

Run after any dataset change. The point: nobody should ever have to read
code to know what the model assumes."""
import os

import pandas as pd

PURPOSE = {
    "sites.csv": "The site universe: who, where (band), how big, incumbent kit, inertia factor.",
    "technologies.csv": "The technology roster: costs, lifetimes, fuel intensities, first years, ramps.",
    "fuel_prices.csv": "Price stacks per fuel: wholesale/network/levies/margin pins + band multipliers.",
    "fuel_emissions.csv": "Emissions factors per fuel per year (grid decarbonisation lives here).",
    "carbon.csv": "Traded/untraded carbon prices and the CBAM phase curve.",
    "finance.csv": "Hurdle rates, discount rate, usage-inertia cost (the calibrated behaviour).",
    "imports.csv": "Import parity prices, embodied carbon, CBAM coverage per commodity.",
    "build_orders.csv": "Committed builds (bounds on new capacity).",
    "committed_events.csv": "Committed closures (demand zeroed from year).",
    "site_overrides.csv": "Site-level demand pins outranking sector trends.",
    "sector_output.csv": "Sector production indices scaling site demand.",
    "outturn.csv": "The scoring truth for the hindcast (UK ETS verified).",
}

LARGE = {"sites.csv"}


def describe(d):
    out = [f"## `{d}/`\n"]
    for f in sorted(os.listdir(d)):
        if not f.endswith(".csv"):
            continue
        df = pd.read_csv(os.path.join(d, f))
        basis = df.basis.value_counts().to_dict() if "basis" in df else {}
        out.append(f"### {f} — {PURPOSE.get(f, '')}")
        out.append(f"{len(df)} rows; basis mix: "
                   + ", ".join(f"{k} {v}" for k, v in sorted(basis.items())))
        if f in LARGE:
            out.append(f"(large file — see the CSV; columns: "
                       f"{', '.join(df.columns)})\n")
        else:
            show = df.drop(columns=[c for c in ("retrieved",) if c in df])
            out.append("\n```\n" + show.to_string(index=False) + "\n```\n")
    return "\n".join(out)


if __name__ == "__main__":
    parts = ["# INPUTS — every lever, generated from the data",
             "", "Regenerate: `python scripts/describe_inputs.py`.", ""]
    for d in ("datasets", "datasets_backcast"):
        if os.path.isdir(d):
            parts.append(describe(d))
    with open("INPUTS.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))
    print("wrote INPUTS.md")
