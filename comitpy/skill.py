"""Forecast-skill scoring (item 8): accuracy is a number that moves per
change, or it is a claim. Mirrors the harness's indexed-trajectory method —
levels embed accounting-boundary offsets; indexed paths score direction and
pace, which is what a forecast is for."""
from __future__ import annotations

import pandas as pd


def indexed_mape(modelled: pd.DataFrame, outturn: pd.DataFrame,
                 base_year: int) -> tuple[float, pd.DataFrame]:
    """Both frames: columns [year, value]. Returns (MAPE over post-base
    years, comparison table indexed to base_year = 100)."""
    m = modelled.set_index("year")["value"]
    o = outturn.set_index("year")["value"]
    years = sorted(set(m.index) & set(o.index))
    if base_year not in years:
        raise ValueError(f"base year {base_year} missing from both series")
    m_idx = 100 * m[years] / m[base_year]
    o_idx = 100 * o[years] / o[base_year]
    tbl = pd.DataFrame({"year": years,
                        "modelled_idx": m_idx.values,
                        "outturn_idx": o_idx.values})
    post = tbl[tbl.year > base_year]
    mape = float((abs(post.modelled_idx - post.outturn_idx)
                  / post.outturn_idx).mean())
    return mape, tbl
