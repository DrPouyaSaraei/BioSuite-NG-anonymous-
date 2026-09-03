"""
tests/test_real_patients.py

Full validation run using the user's REAL patient DVH data (Pinnacle
export, tests/patient_data.xlsx), computing NTCP/TCP with the exact
model parameters from Tables 1 & 2 of Uzan & Nahum (2012), and comparing
qualitatively against the paper's stated findings for each patient.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dvh.pinnacle_excel_import import read_all_patients
from core.ntcp_models import NTCPEndpoint, LKBParams
from core.tcp_models import TCPParams, tcp_lq_poisson_marsden_dvh
from core.optimizer import NTCPLimit, optimise_2d_isotoxic

data = read_all_patients("tests/patient_data.xlsx")

# ---------------------------------------------------------------- #
# Table 1 (NTCP endpoints) and Table 2 (TCP) parameters from the paper
# ---------------------------------------------------------------- #
lung_endpoint = NTCPEndpoint(
    name="lung", model="LKB", alpha_beta=3.0,
    params=LKBParams(td50=2920.0, m=0.45, n=1.0, alpha_beta=3.0),  # Table 1
)
rectum_endpoint = NTCPEndpoint(
    name="rectum", model="LKB", alpha_beta=3.0,
    params=LKBParams(td50=9770.0, m=0.27, n=0.085, alpha_beta=3.0),  # Table 1
)

nsclc_tcp_params = TCPParams(
    alpha=0.307, alpha_beta=10.0, alpha_spread=0.037,
    clonogen_density=1e7,
    repopulation_delay_days=20.9, clonogen_doubling_time_days=3.7,
)  # Table 2, NSCLC row

prostate_tcp_by_ab = {
    10.0: TCPParams(alpha=0.300, alpha_beta=10.0, alpha_spread=0.114, clonogen_density=1e7),
    5.0:  TCPParams(alpha=0.258, alpha_beta=5.0,  alpha_spread=0.099, clonogen_density=1e7),
    3.0:  TCPParams(alpha=0.217, alpha_beta=3.0,  alpha_spread=0.082, clonogen_density=1e7),
    1.5:  TCPParams(alpha=0.155, alpha_beta=1.5,  alpha_spread=0.058, clonogen_density=1e7),
}  # Table 2, prostate rows

# ================================================================== #
print("=" * 78)
print("PATIENT 1 (NSCLC) -- reference plan 55 Gy / 20# -- paper predicts:")
print("  large TCP/NTCP separation -> significant escalation headroom")
print("=" * 78)
p1 = data["Patient 1"]
ptv1, gtv1, lung_gtv1 = p1["PTV"], p1["GTV"], p1["TOTAL LUNG-GTV"]

ntcp_lung1 = lung_endpoint.compute(lung_gtv1, n_fractions=20)
tcp1 = tcp_lq_poisson_marsden_dvh(ptv1, gtv1.total_volume_cm3, nsclc_tcp_params, n_fractions=20)
print(f"GTV volume: {gtv1.total_volume_cm3:.1f} cc   PTV Dmean: {ptv1.mean_dose_cgy/100:.1f} Gy")
print(f"Lung NTCP (pneumonitis) @ 55Gy/20#: {ntcp_lung1:.2%}")
print(f"TCP (PTV, DVH-based)     @ 55Gy/20#: {tcp1:.2%}")

# escalate at constant fraction number (20#) to see TCP/NTCP separation
print("\nDose-escalation sweep (constant #fractions=20, scaling whole DVH):")
print(f"{'Factor':>8} {'TotalDose(Gy)':>14} {'TCP':>8} {'Lung_NTCP':>10}")
for factor in [0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4]:
    ptv_s = ptv1.scale_dose(factor)
    lung_s = lung_gtv1.scale_dose(factor)
    tcp_s = tcp_lq_poisson_marsden_dvh(ptv_s, gtv1.total_volume_cm3, nsclc_tcp_params, n_fractions=20)
    ntcp_s = lung_endpoint.compute(lung_s, n_fractions=20)
    print(f"{factor:8.2f} {ptv1.mean_dose_cgy*factor/100:14.1f} {tcp_s:8.2%} {ntcp_s:10.2%}")

# ================================================================== #
print()
print("=" * 78)
print("PATIENT 2 (NSCLC, larger tumour) -- reference plan 55 Gy / 20# --")
print("  paper predicts: TCP/NTCP curves close together -> escalation unsafe")
print("=" * 78)
p2 = data["Patient 2"]
ptv2, gtv2, lung_gtv2 = p2["PTV"], p2["GTV"], p2["TOTAL LUNG-GTV"]

ntcp_lung2 = lung_endpoint.compute(lung_gtv2, n_fractions=20)
tcp2 = tcp_lq_poisson_marsden_dvh(ptv2, gtv2.total_volume_cm3, nsclc_tcp_params, n_fractions=20)
print(f"GTV volume: {gtv2.total_volume_cm3:.1f} cc   PTV Dmean: {ptv2.mean_dose_cgy/100:.1f} Gy")
print(f"Lung NTCP (pneumonitis) @ 55Gy/20#: {ntcp_lung2:.2%}")
print(f"TCP (PTV, DVH-based)     @ 55Gy/20#: {tcp2:.2%}")

print("\nDose-escalation sweep (constant #fractions=20, scaling whole DVH):")
print(f"{'Factor':>8} {'TotalDose(Gy)':>14} {'TCP':>8} {'Lung_NTCP':>10}")
for factor in [0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4]:
    ptv_s = ptv2.scale_dose(factor)
    lung_s = lung_gtv2.scale_dose(factor)
    tcp_s = tcp_lq_poisson_marsden_dvh(ptv_s, gtv2.total_volume_cm3, nsclc_tcp_params, n_fractions=20)
    ntcp_s = lung_endpoint.compute(lung_s, n_fractions=20)
    print(f"{factor:8.2f} {ptv2.mean_dose_cgy*factor/100:14.1f} {tcp_s:8.2%} {ntcp_s:10.2%}")

print(f"\n=> Patient 1 TCP-NTCP gap @ reference dose: {tcp1-ntcp_lung1:+.1%}")
print(f"=> Patient 2 TCP-NTCP gap @ reference dose: {tcp2-ntcp_lung2:+.1%}")
print("   (paper: Patient 1 gap should be much larger than Patient 2's)")

# ================================================================== #
print()
print("=" * 78)
print("PATIENT 3 (Prostate) -- reference plan 74 Gy / 37# --")
print("  paper predicts: hypofractionation viable for low tumour alpha/beta")
print("=" * 78)
p3 = data["Patient 3"]
ptv3, rectum3 = p3["PTV"], p3["Rectum"]

ntcp_rectum_ref = rectum_endpoint.compute(rectum3, n_fractions=37)
print(f"PTV Dmean: {ptv3.mean_dose_cgy/100:.1f} Gy   Rectum NTCP @ 74Gy/37#: {ntcp_rectum_ref:.2%}")

print("\n2D isotoxic optimisation (5-50 fractions), NTCP limit = reference value,")
print("for each tumour alpha/beta (paper Figure 5):")

for ab, tcp_params in prostate_tcp_by_ab.items():
    def tcp_fn(total_dose_cgy, n_fractions, _ptv=ptv3, _params=tcp_params, _ref=ptv3.mean_dose_cgy):
        factor = total_dose_cgy / _ref
        scaled = _ptv.scale_dose(factor)
        # prostate GTV ~ PTV volume here (no separate GTV structure supplied)
        return tcp_lq_poisson_marsden_dvh(scaled, _ptv.total_volume_cm3, _params, n_fractions)

    ntcp_limit = NTCPLimit(endpoint=rectum_endpoint, limit=ntcp_rectum_ref)
    results = optimise_2d_isotoxic(
        fraction_range=range(5, 51, 5),
        dvh_by_structure={"rectum": rectum3},
        ntcp_limits=[ntcp_limit],
        tcp_fn=tcp_fn,
        reference_dose_cgy=ptv3.mean_dose_cgy,
        dose_search_range_cgy=(500.0, 20000.0),
    )
    tcp_5fx = results[0].tcp
    tcp_50fx = results[-1].tcp
    trend = "hypofractionation FAVOURED" if tcp_5fx > tcp_50fx else "standard fractionation favoured"
    print(f"  alpha/beta={ab:4.1f} Gy: TCP(5#)={tcp_5fx:6.1%}  TCP(50#)={tcp_50fx:6.1%}  -> {trend}")

print()
print("Done.")
