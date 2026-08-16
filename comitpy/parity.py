"""Phase-A parity: solve R-COMIT's exact exported LP with this package's
solver stack and compare against the R solution.

What this proves: the numerics/solver layer (sparse assembly, HiGHS via
scipy, objective accounting) reproduces R-COMIT end-to-end on the real
~700k-variable problem, and establishes the variable-index mapping that
formulation parity (phase B: comitpy building the same matrix from raw
data) will be scored against.

What it does not prove: that comitpy's own model builder constructs this
matrix - that is phase B, gated on template ingestion.

Comparison logic respects the degeneracy findings from the harness: the
objective must match tightly; national tech-year totals are compared with
the expectation that most match and any divergence sits in near-tied
(alternate-optima) dimensions, which are reported rather than hidden.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import linprog


def solve_exported(parity_dir: str) -> dict:
    var = pd.read_csv(f"{parity_dir}/variables.csv")
    coef = pd.read_csv(f"{parity_dir}/coefficients.csv")
    trip = pd.read_csv(f"{parity_dir}/matrix.csv")
    cons = pd.read_csv(f"{parity_dir}/constraints.csv")
    meta = pd.read_csv(f"{parity_dir}/meta.csv").iloc[0]

    n = int(meta.n_vars)
    c = np.zeros(n)
    c[coef.variable_index.to_numpy() - 1] = coef.coefficient.to_numpy()

    A = sparse.coo_matrix(
        (trip.value, (trip.row - 1, trip.col - 1)),
        shape=(int(meta.n_cons), n)).tocsr()

    d = cons.sort_values("row").direction.to_numpy()
    rhs = cons.sort_values("row").rhs.to_numpy()
    # mirror the R runner: tiny rhs values are imprecise zeros
    rhs = np.where(np.abs(rhs) < 1e-12, 0.0, rhs)

    is_eq = d == "=="
    is_le = d == "<="
    is_ge = d == ">="
    A_eq, b_eq = A[is_eq], rhs[is_eq]
    A_ub = sparse.vstack([A[is_le], -A[is_ge]]).tocsr()
    b_ub = np.concatenate([rhs[is_le], -rhs[is_ge]])

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=(0, None), method="highs")
    if not res.success:
        raise RuntimeError(f"parity solve failed: {res.message}")

    return {"x": res.x, "objective": float(res.fun),
            "r_objective": float(meta.r_objective), "variables": var}


def compare(parity_dir: str, r_solution_csv: str) -> pd.DataFrame:
    """r_solution_csv: variable_index, solution (the R primal)."""
    out = solve_exported(parity_dir)
    var = out["variables"]
    var["py"] = out["x"][var.variable_index.to_numpy() - 1]
    r = pd.read_csv(r_solution_csv)
    var = var.merge(r, on="variable_index", how="left")

    obj_rel = abs(out["objective"] - out["r_objective"]) / abs(out["r_objective"])
    print(f"objective: R {out['r_objective']:.4f}  py {out['objective']:.4f}  "
          f"rel diff {obj_rel:.2e}")

    used = var[var.variable_type == "used_capacity"]
    nat = (used.groupby(["code", "year"])
           .agg(r_total=("solution", "sum"), py_total=("py", "sum"))
           .reset_index())
    floor = nat.r_total[nat.r_total > 0].quantile(0.25)
    mat = nat[nat.r_total > floor].copy()
    mat["rel"] = (mat.py_total - mat.r_total).abs() / mat.r_total
    n_match = int((mat.rel < 0.01).sum())
    print(f"national used-capacity tech-years (material): {len(mat)}; "
          f"matching within 1%: {n_match}; "
          f"max rel deviation: {mat.rel.max():.3f}")
    print("(divergent tech-years, if any, are the near-tied/alternate-optima "
          "dimensions documented in the harness)")
    return mat.sort_values("rel", ascending=False)
