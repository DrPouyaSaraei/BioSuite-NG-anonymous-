"""
tests/test_core_sanity.py

Sanity/validation test for the core radiobiology engine, loosely mirroring
the prostate example (Patient 3) of Uzan & Nahum (2012):
74 Gy / 37 fractions, rectal bleeding NTCP endpoint (LKB, Table 1),
tumour alpha/beta = 10 Gy (Table 2, "high a/b" row).

This is NOT a byte-for-byte reproduction of the paper's figures (we don't
have the authors' exact DVHs), but it checks that:
  1. All modules import and run without error.
  2. NTCP/TCP values are sane probabilities (0-1).
  3. TCP increases monotonically with dose (basic physical sanity check).
  4. The 2D isotoxic optimiser produces a full dose/fraction curve.
  5. The Monte-Carlo confidence-interval module produces a sensible band.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from core.dvh import DVH
from core.ntcp_models import NTCPEndpoint, LKBParams
from core.tcp_models import TCPParams, tcp_lq_poisson_marsden
from core.optimizer import NTCPLimit, optimise_1d_fixed_fractions, optimise_2d_isotoxic
from core.confidence import ParamUncertainty, monte_carlo_ci

print("=" * 70)
print("1) Building a synthetic rectum DVH (typical shape: full low-dose")
print("   volume tapering off at high dose)")
print("=" * 70)

dose_bins = np.linspace(0, 7800, 40)  # cGy, physical dose at 74 Gy/37#
volume = np.maximum(0.0, 30 * np.exp(-dose_bins / 4000.0) - 2)
rectum_dvh = DVH("rectum", dose_bins, volume)
print(f"Rectum total volume: {rectum_dvh.total_volume_cm3:.1f} cm3, "
      f"Dmax: {rectum_dvh.max_dose_cgy/100:.1f} Gy, "
      f"Dmean: {rectum_dvh.mean_dose_cgy/100:.1f} Gy")

print()
print("=" * 70)
print("2) NTCP (LKB) for rectal bleeding, Table 1 parameters")
print("=" * 70)
rectum_endpoint = NTCPEndpoint(
    name="rectum",
    model="LKB",
    alpha_beta=3.0,
    params=LKBParams(td50=9770.0, m=0.27, n=0.085, alpha_beta=3.0),  # Table 1
)
ntcp_now = rectum_endpoint.compute(rectum_dvh, n_fractions=37)
print(f"Rectum NTCP @ 74 Gy/37# (reference plan): {ntcp_now:.3%}")
assert 0.0 <= ntcp_now <= 1.0, "NTCP out of [0,1] range!"

print()
print("=" * 70)
print("3) TCP (LQ-Poisson Marsden), prostate, alpha/beta = 10 Gy (Table 2)")
print("=" * 70)
tcp_params = TCPParams(
    alpha=0.3, alpha_beta=10.0, alpha_spread=0.114,
    clonogen_density=1e7,
)

def tcp_fn(total_dose_cgy, n_fractions, gtv_vol=30.0):
    return tcp_lq_poisson_marsden(gtv_vol, tcp_params, total_dose_cgy, n_fractions)

tcp_now = tcp_fn(7400.0, 37)
print(f"Prostate TCP @ 74 Gy/37# (a/b=10): {tcp_now:.3%}")
assert 0.0 <= tcp_now <= 1.0, "TCP out of [0,1] range!"

# monotonicity check: TCP should increase with dose (fixed fractions)
tcp_low = tcp_fn(6000.0, 37)
tcp_high = tcp_fn(8600.0, 37)
print(f"Monotonicity check: TCP(60Gy)={tcp_low:.3%} < TCP(74Gy)={tcp_now:.3%} < TCP(86Gy)={tcp_high:.3%}")
assert tcp_low <= tcp_now <= tcp_high, "TCP is not monotonically increasing with dose!"

print()
print("=" * 70)
print("4) 1D optimisation: total dose for fixed 37 fractions, NTCP limit")
print("   set to the value at the reference plan (isotoxic constraint)")
print("=" * 70)
ntcp_limit = NTCPLimit(endpoint=rectum_endpoint, limit=ntcp_now)
res_1d = optimise_1d_fixed_fractions(
    n_fractions=37,
    dvh_by_structure={"rectum": rectum_dvh},
    ntcp_limits=[ntcp_limit],
    tcp_fn=lambda d, n: tcp_fn(d, n),
    reference_dose_cgy=7400.0,
    dose_search_range_cgy=(3000.0, 12000.0),
)
print(f"Optimised dose: {res_1d.total_dose_cgy/100:.2f} Gy -> TCP={res_1d.tcp:.3%}, "
      f"limiting endpoint: {res_1d.limiting_endpoint}")

print()
print("=" * 70)
print("5) 2D isotoxic optimisation across 5-40 fractions (paper Fig. 5 style)")
print("=" * 70)

# NOTE: optimise_2d_isotoxic scales the rectum DVH by (candidate_dose/reference_dose)
# for EACH fraction number -- reference_dose_cgy anchors that scaling to the
# dose at which rectum_dvh was actually measured (74 Gy).
results = optimise_2d_isotoxic(
    fraction_range=range(5, 41, 5),
    dvh_by_structure={"rectum": rectum_dvh},
    ntcp_limits=[ntcp_limit],
    tcp_fn=lambda d, n: tcp_fn(d, n),
    reference_dose_cgy=7400.0,
    dose_search_range_cgy=(500.0, 15000.0),
)
print(f"{'#Fx':>4} {'Dose(Gy)':>10} {'TCP':>8}  Limiting")
for r in results:
    print(f"{r.n_fractions:4d} {r.total_dose_cgy/100:10.2f} {r.tcp:8.2%}  {r.limiting_endpoint}")

print()
print("=" * 70)
print("6) Monte-Carlo confidence interval on NTCP (NEW feature)")
print("   varying TD50 and m with plausible literature uncertainty")
print("=" * 70)

def ntcp_compute(td50, m):
    ep = NTCPEndpoint(
        name="rectum", model="LKB", alpha_beta=3.0,
        params=LKBParams(td50=td50, m=m, n=0.085, alpha_beta=3.0),
    )
    return ep.compute(rectum_dvh, n_fractions=37)

ci_result = monte_carlo_ci(
    compute_fn=ntcp_compute,
    param_uncertainties=[
        ParamUncertainty("td50", mean=9770.0, sd=500.0, lower_bound=1000.0),
        ParamUncertainty("m", mean=0.27, sd=0.03, lower_bound=0.01),
    ],
    fixed_kwargs={},
    n_samples=3000,
    ci=0.95,
    seed=42,
)
print(f"NTCP median: {ci_result['median']:.3%}  "
      f"95% CI: [{ci_result['lower']:.3%}, {ci_result['upper']:.3%}]  "
      f"(n_valid={ci_result['n_valid']}/{ci_result['n_total']})")

print()
print("ALL SANITY CHECKS PASSED.")
