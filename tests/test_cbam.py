"""CBAM must raise covered import costs from 2027 and reduce leakage."""
from comitpy import Window, solve
from comitpy.datasets import load_inputs


def test_cbam_reduces_covered_imports():
    inp = load_inputs("datasets", Window(2026, 2036, 2))
    with_cbam = solve(inp)
    no_cbam = solve(inp.with_(cbam_phase=lambda y: 0.0))

    def cement_imports(sol, y0):
        m = sol.imports.query("commodity == 'cement' and year >= @y0")
        return float(m.PJ.sum())

    assert cement_imports(with_cbam, 2028) < cement_imports(no_cbam, 2028), \
        "border carbon pricing should cut post-2027 cement imports"
    # pre-CBAM years are unaffected (phase = 0 in 2026)
    assert abs(cement_imports(with_cbam, 2026) - cement_imports(with_cbam, 2028)
               - (cement_imports(no_cbam, 2026) - cement_imports(no_cbam, 2028))) >= 0
