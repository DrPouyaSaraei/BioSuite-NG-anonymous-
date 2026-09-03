"""
tests/test_ui_workflow.py
Headless (offscreen) end-to-end test of the full UI workflow using
Patient 3 (prostate) real data: create plan -> import DVH -> define
endpoints -> associate -> run isotoxic optimisation -- exercising every
tab's core logic exactly as a user clicking through the app would.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)

from ui.app_state import AppState, TreatmentPlan, EndpointDefinition
from dvh.pinnacle_excel_import import read_pinnacle_sheet
from core.ntcp_models import NTCPEndpoint, LKBParams
from core.tcp_models import TCPParams
from ui.tab_treatment_plans import TreatmentPlansTab
from ui.tab_dvh_import import DVHImportTab
from ui.tab_model_params import ModelEndpointTab
from ui.tab_dvh_plots import DVHPlotsTab
from ui.tab_optimisation import OptimisationTab

state = AppState()

# 1) Treatment plans tab: add a plan (as if user typed into the form + clicked "Add plan")
tp_tab = TreatmentPlansTab(state)
tp_tab.plan_id_edit.setText("Patient3_Prostate")
tp_tab.fractions_edit.setText("37")
tp_tab.dose_edit.setText("7400")
tp_tab.on_add_plan()
assert "Patient3_Prostate" in state.plans
print("[OK] Treatment plan added via UI:", state.plans["Patient3_Prostate"])

# 2) DVH import tab: load real Pinnacle DVHs directly (bypassing file dialog, same as
#    what happens after the user picks the file+sheet in on_load_dvh)
dvh_tab = DVHImportTab(state)
structs = read_pinnacle_sheet("tests/patient_data.xlsx", "Patient 3")
plan = state.active_plan()
for name, dvh in structs.items():
    dvh_tab._register_dvh(plan, name, dvh, "tests/patient_data.xlsx [Patient 3]", "Excel")
dvh_tab.refresh_table()
assert dvh_tab.table.rowCount() == len(structs)
print(f"[OK] DVH import tab loaded {dvh_tab.table.rowCount()} structures:", list(plan.dvhs.keys()))

# 3) Model/Endpoint parameters tab: define Rectum NTCP + Prostate TCP endpoints
mp_tab = ModelEndpointTab(state)
rectum_ep = EndpointDefinition(
    name="Rectum bleeding", kind="NTCP", model="LKB",
    ntcp_endpoint=NTCPEndpoint(name="Rectum bleeding", model="LKB", alpha_beta=3.0,
                                params=LKBParams(td50=9770.0, m=0.27, n=0.085, alpha_beta=3.0)),
)
prostate_ep = EndpointDefinition(
    name="Prostate TCP", kind="TCP", model="Marsden (LQ-Poisson)",
    tcp_params=TCPParams(alpha=0.3, alpha_beta=10.0, alpha_spread=0.114, clonogen_density=1e7),
    gtv_volume_cm3=structs["Prostate + Seminal Vesicle"].total_volume_cm3,
)
state.add_endpoint(rectum_ep)
state.add_endpoint(prostate_ep)
mp_tab.refresh()
assert mp_tab.table.rowCount() == 2
print("[OK] Model/Endpoint parameters tab: 2 endpoints defined")

# 4) associate structures to endpoints (as the DVH import tab's "Associate to DVH(s)" would)
plan.dvh_associations["Rectum"] = "Rectum bleeding"
plan.dvh_associations["PTV"] = "Prostate TCP"

# 5) DVH plots tab: refresh + read out current TCP/NTCP
plots_tab = DVHPlotsTab(state)
plots_tab.refresh()
print(f"[OK] DVH plots tab readouts: TCP={plots_tab.tcp_label.text()}  NTCP={plots_tab.ntcp_label.text()}")

# 6) Optimisation tab: run the real isotoxic optimisation exactly as clicking "Run" would
opt_tab = OptimisationTab(state)
opt_tab.fraction_lo, opt_tab.fraction_hi = 5, 45
opt_tab.refresh_table()
opt_tab.run_optimisation()
print(f"[OK] Optimisation tab: best = {opt_tab.best_nf_label.text()} fractions, "
      f"{opt_tab.best_dose_label.text()}, {opt_tab.best_score_label.text()}")

print("\nALL UI WORKFLOW STEPS PASSED.")
