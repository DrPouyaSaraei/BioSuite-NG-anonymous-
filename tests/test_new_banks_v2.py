"""
tests/test_new_banks_v2.py
End-to-end test of BOTH new banks (NTCP v2, TCP -- built from
TCP_NTCP_Unified_English_Parameters.xlsx) using the real Patient 3
(prostate) DVHs: adds a Rectum NTCP endpoint from the new NTCP bank and
a Prostate TCP endpoint from the new TCP bank, associates them, and
computes both -- exercising the exact UI code paths a user would hit.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox
app = QApplication(sys.argv)
QMessageBox.warning = staticmethod(lambda *a, **k: None)

from ui.app_state import AppState, TreatmentPlan
from dvh.pinnacle_excel_import import read_pinnacle_sheet
from ui.dialog_add_from_bank import AddFromBankDialog
from ui.dialog_add_tcp_from_bank import AddTCPFromBankDialog
from ui.tab_dvh_plots import DVHPlotsTab
from ui.tab_optimisation import OptimisationTab

print("=" * 70)
print("1) Setting up Patient 3 (prostate) plan with real DVHs")
print("=" * 70)
state = AppState()
plan = TreatmentPlan(plan_id="P3_NewBanks", fractions=37, prescription_dose_cgy=7400)
state.add_plan(plan)
structs = read_pinnacle_sheet("tests/patient_data.xlsx", "Patient 3")
for name, dvh in structs.items():
    plan.dvhs[name] = dvh
print("Structures:", list(plan.dvhs.keys()))

print()
print("=" * 70)
print("2) Adding Rectum NTCP endpoint from the NEW NTCP bank (v2)")
print("=" * 70)
ntcp_dlg = AddFromBankDialog()
ntcp_dlg.organ_combo.setCurrentText("Rectum")
ntcp_endpoints = [ntcp_dlg.endpoint_combo.itemText(i) for i in range(ntcp_dlg.endpoint_combo.count())]
print("Rectum endpoints available:", ntcp_endpoints)
# pick the QUANTEC-equivalent "late toxicity / rectal bleeding" endpoint
target_ep = next(e for e in ntcp_endpoints if "toxicity" in e.lower())
ntcp_dlg.endpoint_combo.setCurrentText(target_ep)
authors = [ntcp_dlg.author_combo.itemText(i) for i in range(ntcp_dlg.author_combo.count())]
print("Author options:", authors)
ntcp_dlg.alpha_beta_edit.setText("3.0")
ntcp_dlg._on_accept()
assert ntcp_dlg.result_endpoint is not None, "NTCP bank endpoint creation failed"
state.add_endpoint(ntcp_dlg.result_endpoint)
plan.dvh_associations["Rectum"] = ntcp_dlg.result_endpoint.name
ntcp_value = ntcp_dlg.result_endpoint.ntcp_endpoint.compute(plan.dvhs["Rectum"], 37)
print(f"Rectum NTCP ({target_ep}, {authors[0]}): {ntcp_value:.2%}")

print()
print("=" * 70)
print("3) Adding Prostate TCP endpoint from the NEW TCP bank")
print("=" * 70)
tcp_dlg = AddTCPFromBankDialog()
sites = [tcp_dlg.site_combo.itemText(i) for i in range(tcp_dlg.site_combo.count())]
print("TCP bank tumour sites:", sites)
tcp_dlg.site_combo.setCurrentText("Prostate")
prostate_endpoints = [tcp_dlg.endpoint_combo.itemText(i) for i in range(tcp_dlg.endpoint_combo.count())]
print("Prostate endpoints:", prostate_endpoints)
tcp_dlg.endpoint_combo.setCurrentText(next(e for e in prostate_endpoints if "EUD" in e))
recs = [tcp_dlg.record_combo.itemText(i) for i in range(tcp_dlg.record_combo.count())]
print("Prostate/TCP-EUD records:", recs)
# P003 (Wang 2003) is 'computable_full' with sublethal-repair detail
p003 = next(r for r in recs if "P003" in r)
tcp_dlg.record_combo.setCurrentText(p003)
print("Missing fields for P003:", list(tcp_dlg._fill_edits.keys()))
gtv_vol = structs["Prostate + Seminal Vesicle"].total_volume_cm3
tcp_dlg.gtv_vol_edit.setText(str(gtv_vol))
for key, edit in tcp_dlg._fill_edits.items():
    if key == "alpha_spread":
        edit.setText("0.05")
tcp_dlg._on_accept()
assert tcp_dlg.result_endpoint is not None, "TCP bank endpoint creation failed"
state.add_endpoint(tcp_dlg.result_endpoint)
plan.dvh_associations["PTV"] = tcp_dlg.result_endpoint.name

from core.tcp_models import tcp_lq_poisson_marsden_dvh
tcp_value = tcp_lq_poisson_marsden_dvh(
    plan.dvhs["PTV"], gtv_vol, tcp_dlg.result_endpoint.tcp_params, 37
)
print(f"Prostate TCP (P003 Wang et al. 2003, K={3.0e6:.0e} clonogens / {gtv_vol:.1f}cc): {tcp_value:.2%}")

print()
print("=" * 70)
print("4) Full UI round-trip: DVH plots tab + Optimisation tab")
print("=" * 70)
dvh_tab = DVHPlotsTab(state)
dvh_tab.refresh()
print(f"DVH plots readouts: TCP={dvh_tab.tcp_label.text()}  NTCP={dvh_tab.ntcp_label.text()}")

opt_tab = OptimisationTab(state)
opt_tab.fraction_lo, opt_tab.fraction_hi = 15, 40
opt_tab.refresh_table()
opt_tab.run_optimisation()
print(f"Optimisation: best = {opt_tab.best_nf_label.text()} fractions, "
      f"{opt_tab.best_dose_label.text()}, {opt_tab.best_score_label.text()}")

print()
print("ALL NEW-BANK END-TO-END CHECKS PASSED.")
