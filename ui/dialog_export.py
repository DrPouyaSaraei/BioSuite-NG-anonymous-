"""
ui/dialog_export.py
"Export..." dialog, reachable from the Radiobiology menu, so the user can
get data OUT of BioSuite-NG without hunting through individual tabs:
  - NTCP/TCP summary for the active plan (CSV)
  - Raw DVH data for the active plan's structures (CSV)
  - The current endpoint list (JSON) -- reuses the same format as
    Model/Endpoint parameters' Save list.
"""
from __future__ import annotations
import csv
import json
import dataclasses
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QMessageBox, QRadioButton, QGroupBox
)

from ui.app_state import AppState


class ExportDialog(QDialog):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.setWindowTitle("Export")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        plan = self.state.active_plan()
        plan_label = QLabel(f"Active plan: <b>{plan.plan_id if plan else '(none)'}</b>")
        layout.addWidget(plan_label)

        box = QGroupBox("What do you want to export?")
        box_l = QVBoxLayout(box)
        self.opt_summary = QRadioButton("NTCP/TCP summary for the active plan (CSV)")
        self.opt_summary.setChecked(True)
        self.opt_dvh = QRadioButton("Raw DVH data for the active plan's structures (CSV)")
        self.opt_endpoints = QRadioButton("Endpoint list (JSON, same format as Save list)")
        box_l.addWidget(self.opt_summary)
        box_l.addWidget(self.opt_dvh)
        box_l.addWidget(self.opt_endpoints)
        layout.addWidget(box)

        btn_row = QHBoxLayout()
        export_btn = QPushButton("Export...")
        export_btn.clicked.connect(self.on_export)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addStretch()
        btn_row.addWidget(export_btn)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------ #
    def on_export(self):
        if self.opt_summary.isChecked():
            self._export_summary()
        elif self.opt_dvh.isChecked():
            self._export_dvh()
        else:
            self._export_endpoints()

    def _export_summary(self):
        plan = self.state.active_plan()
        if plan is None:
            QMessageBox.information(self, "No active plan", "Select/create a treatment plan first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export NTCP/TCP summary",
                                               f"{plan.plan_id}_ntcp_tcp_summary.csv", "CSV files (*.csv)")
        if not path:
            return
        from ui.tcp_ntcp_compute import compute_tcp
        rows = [["Structure", "Endpoint", "Model", "Kind", "Value (%)"]]
        for struct_name, ep_name in plan.dvh_associations.items():
            dvh = plan.dvhs.get(struct_name)
            ep = self.state.endpoints.get(ep_name)
            if dvh is None or ep is None:
                continue
            if ep.kind == "NTCP" and ep.ntcp_endpoint is not None:
                value = ep.ntcp_endpoint.compute(dvh, plan.fractions) * 100
            elif ep.kind == "TCP" and ep.tcp_params is not None:
                value = compute_tcp(ep, dvh, plan.fractions) * 100
            else:
                continue
            rows.append([struct_name, ep_name, ep.model, ep.kind, f"{value:.2f}"])
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(rows)
            QMessageBox.information(self, "Exported", f"Saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export error", str(e))

    def _export_dvh(self):
        plan = self.state.active_plan()
        if plan is None or not plan.dvhs:
            QMessageBox.information(self, "No DVH data", "Import at least one DVH first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export DVH data",
                                               f"{plan.plan_id}_dvh_data.csv", "CSV files (*.csv)")
        if not path:
            return
        rows = [["Structure", "Dose_cGy", "Volume_cm3"]]
        for name, dvh in plan.dvhs.items():
            for d, v in zip(dvh.dose_bins_cgy, dvh.volume_cm3):
                rows.append([name, f"{d:.3f}", f"{v:.5f}"])
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(rows)
            QMessageBox.information(self, "Exported", f"Saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export error", str(e))

    def _export_endpoints(self):
        if not self.state.endpoints:
            QMessageBox.information(self, "No endpoints", "Define at least one endpoint first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export endpoint list",
                                               "endpoints.json", "JSON files (*.json)")
        if not path:
            return
        data = []
        for ep in self.state.endpoints.values():
            d = {"name": ep.name, "kind": ep.kind, "model": ep.model}
            if ep.kind == "NTCP" and ep.ntcp_endpoint is not None:
                d["alpha_beta"] = ep.ntcp_endpoint.alpha_beta
                d["params"] = dataclasses.asdict(ep.ntcp_endpoint.params)
            elif ep.tcp_params is not None:
                d["params"] = dataclasses.asdict(ep.tcp_params)
                d["gtv_volume_cm3"] = ep.gtv_volume_cm3
            data.append(d)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            QMessageBox.information(self, "Exported", f"Saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export error", str(e))
