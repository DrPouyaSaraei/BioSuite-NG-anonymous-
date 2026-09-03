"""
ui/tab_dvh_import.py
Mirrors the original "DVH import" tab:
  - Load DVH / Load Eclipse DVH buttons
  - Associated organ/endpoint combo + "Associate to DVH(s)" button
  - Remove DVH button
  - table: Name | Organ/Endpoint | Type | File location | Max/Min/Avg dose (cGy) | EUD (cGy) | Vol (cc) | Plan ID
"""
from __future__ import annotations
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox,
    QInputDialog
)

from ui.app_state import AppState
from core.dvh import DVH, read_dvh_csv, read_dicom_rtdose_structure
from core.ntcp_niemierko import niemierko_geud
from dvh.pinnacle_excel_import import read_pinnacle_sheet
from dvh.excel_import import read_dvhs_from_excel, list_sheets


class DVHImportTab(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        # loaded_dvhs: list of (name, dvh, file_location, dvh_type)
        self._loaded = []  # rows shown in the table, each dict
        self._build_ui()
        self.state.plans_changed.connect(self.refresh_associated_combo)
        self.state.endpoints_changed.connect(self.refresh_associated_combo)
        self.state.active_plan_changed.connect(lambda _: self.refresh_table())

    def _build_ui(self):
        layout = QVBoxLayout(self)

        btn_row = QHBoxLayout()
        self.load_btn = QPushButton("Load DVH")
        self.load_btn.setToolTip("Excel (Pinnacle-style or wide/long), CSV, or DICOM-RT")
        self.load_dicom_btn = QPushButton("Load Eclipse/DICOM DVH")
        self.accumulate_btn = QPushButton("Accumulate DVHs (4D) [NEW]")
        self.accumulate_btn.setToolTip(
            "Combine 2+ selected DVHs of the SAME structure (e.g. breathing "
            "phases, or primary+boost courses) into one accumulated DVH "
            "(core/dose_accumulation.py) -- not in the original BioSuite."
        )
        btn_row.addWidget(self.load_btn)
        btn_row.addWidget(self.load_dicom_btn)
        btn_row.addWidget(self.accumulate_btn)
        btn_row.addStretch()

        self.assoc_label = QLabel("Associated organ/endpoint")
        self.assoc_combo = QComboBox()
        self.assoc_btn = QPushButton("Associate to DVH(s)")
        self.remove_btn = QPushButton("Remove DVH")

        assoc_row = QHBoxLayout()
        assoc_col = QVBoxLayout()
        assoc_col.addWidget(self.assoc_combo)
        assoc_col.addWidget(self.assoc_label)
        assoc_row.addLayout(assoc_col)
        assoc_row.addWidget(self.assoc_btn)
        assoc_row.addWidget(self.remove_btn)
        assoc_row.addStretch()

        layout.addLayout(btn_row)
        layout.addLayout(assoc_row)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Name", "Organ/Endpoint", "Type", "File location",
            "Max/Min/Avg dose (cGy)", "EUD (cGy)", "Vol (cc)", "Plan ID"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self.table)

        self.load_btn.clicked.connect(self.on_load_dvh)
        self.load_dicom_btn.clicked.connect(self.on_load_dicom)
        self.assoc_btn.clicked.connect(self.on_associate)
        self.remove_btn.clicked.connect(self.on_remove)
        self.accumulate_btn.clicked.connect(self.on_accumulate)

    # ------------------------------------------------------------------ #
    def refresh_associated_combo(self):
        self.assoc_combo.clear()
        self.assoc_combo.addItems(sorted(self.state.endpoints.keys()))

    def _active_plan_or_warn(self):
        plan = self.state.active_plan()
        if plan is None:
            QMessageBox.warning(self, "No active plan",
                                 "Create/select a treatment plan first (Treatment plans tab).")
        return plan

    # ------------------------------------------------------------------ #
    def on_load_dvh(self):
        plan = self._active_plan_or_warn()
        if plan is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Load DVH", "", "DVH files (*.xlsx *.xls *.csv);;All files (*.*)"
        )
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".csv":
                dvh = read_dvh_csv(path)
                self._register_dvh(plan, dvh.structure_name, dvh, path, "CSV")
            else:  # .xlsx / .xls
                sheets = list_sheets(path)
                sheet = sheets[0]
                if len(sheets) > 1:
                    sheet, ok = QInputDialog.getItem(
                        self, "Select sheet (patient)", "Sheet:", sheets, 0, False
                    )
                    if not ok:
                        return
                # try Pinnacle block format first, fall back to generic wide/long
                try:
                    structs = read_pinnacle_sheet(path, sheet)
                    if not structs:
                        raise ValueError("empty")
                except Exception:
                    structs = read_dvhs_from_excel(path, sheet_name=sheet)
                for name, dvh in structs.items():
                    self._register_dvh(plan, name, dvh, f"{path} [{sheet}]", "Excel")
        except Exception as e:
            QMessageBox.critical(self, "Import error", f"Failed to read DVH:\n{e}")
            return
        self.refresh_table()
        self.state.dvh_data_changed.emit()

    def on_load_dicom(self):
        plan = self._active_plan_or_warn()
        if plan is None:
            return
        rtdose_path, _ = QFileDialog.getOpenFileName(self, "Select RTDOSE file", "", "DICOM (*.dcm)")
        if not rtdose_path:
            return
        rtstruct_path, _ = QFileDialog.getOpenFileName(self, "Select RTSTRUCT file", "", "DICOM (*.dcm)")
        if not rtstruct_path:
            return
        struct_name, ok = QInputDialog.getText(self, "Structure name", "Structure name (as in RTSTRUCT):")
        if not ok or not struct_name:
            return
        try:
            dvh = read_dicom_rtdose_structure(rtdose_path, rtstruct_path, struct_name)
        except ImportError as e:
            QMessageBox.critical(self, "Missing dependency", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "DICOM import error", str(e))
            return
        self._register_dvh(plan, struct_name, dvh, f"{rtdose_path} + {rtstruct_path}", "DICOM-RT")
        self.refresh_table()
        self.state.dvh_data_changed.emit()

    def _register_dvh(self, plan, name, dvh: DVH, file_location: str, dvh_type: str):
        # de-duplicate name within this plan
        key = name
        suffix = 2
        while key in plan.dvhs:
            key = f"{name}_{suffix}"
            suffix += 1
        plan.dvhs[key] = dvh
        self._loaded.append({
            "name": key, "dvh": dvh, "file": file_location,
            "type": dvh_type, "plan_id": plan.plan_id,
        })

    # ------------------------------------------------------------------ #
    def on_associate(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        if not rows:
            QMessageBox.information(self, "No selection", "Select one or more DVH rows first.")
            return
        endpoint_name = self.assoc_combo.currentText()
        if not endpoint_name:
            QMessageBox.information(self, "No endpoint", "Define an endpoint first "
                                                          "(Model/Endpoint parameters tab).")
            return
        for r in rows:
            name = self.table.item(r, 0).text()
            plan_id = self.table.item(r, 7).text()
            plan = self.state.plans.get(plan_id)
            if plan:
                plan.dvh_associations[name] = endpoint_name
        self.refresh_table()
        self.state.dvh_data_changed.emit()

    def on_remove(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            name = self.table.item(r, 0).text()
            plan_id = self.table.item(r, 7).text()
            plan = self.state.plans.get(plan_id)
            if plan:
                plan.dvhs.pop(name, None)
                plan.dvh_associations.pop(name, None)
        self._loaded = [d for d in self._loaded
                         if not (d["plan_id"] in self.state.plans
                                 and d["name"] not in self.state.plans[d["plan_id"]].dvhs)]
        self.refresh_table()
        self.state.dvh_data_changed.emit()

    # ------------------------------------------------------------------ #
    def _compute_display_eud_cgy(self, dvh: DVH, endpoint_name: str, n_fractions: int) -> str:
        """
        Real generalised-EUD (Niemierko formula), computed on the EQD2-corrected
        DVH using the volume exponent 'a' implied by the associated endpoint's
        model:
            LKB          -> a = 1/n           (n = LKB's own volume parameter)
            EUD/Niemierko-> a = the endpoint's own 'a' parameter directly
            RS           -> a ~= 1/s          (rough LKB-equivalent mapping; RS
                                                 doesn't define an EUD natively)
            SMD          -> not defined for a point-dose model -> '--'
            TCP endpoints-> a = -10           (conventional very-negative exponent
                                                 that weights cold spots, standard
                                                 practice for tumour gEUD)
            (no association) -> a = 1 (arithmetic mean dose), alpha/beta = 3 Gy default
        NOTE: earlier versions of this table incorrectly showed the *mean dose*
        in this column for every row -- that placeholder has been replaced with
        this real gEUD calculation.
        """
        ep = self.state.endpoints.get(endpoint_name) if endpoint_name else None

        if ep is None:
            eqd2 = dvh.to_eqd2(n_fractions, 3.0)
            return f"{niemierko_geud(eqd2, a=1.0):.0f}*"  # '*' flags the no-endpoint fallback

        if ep.kind == "NTCP" and ep.ntcp_endpoint is not None:
            alpha_beta = ep.ntcp_endpoint.alpha_beta
            eqd2 = dvh.to_eqd2(n_fractions, alpha_beta)
            model = ep.ntcp_endpoint.model
            if model == "LKB":
                n = ep.ntcp_endpoint.params.n
                a = 1.0 / n if n != 0 else 1.0
            elif model == "EUD":
                a = ep.ntcp_endpoint.params.a
            elif model == "RS":
                s = max(ep.ntcp_endpoint.params.s, 1e-3)
                a = 1.0 / s
            else:  # SMD -- point-dose model, EUD not applicable
                return "--"
            return f"{niemierko_geud(eqd2, a):.0f}"

        if ep.kind == "TCP" and ep.tcp_params is not None:
            alpha_beta = ep.tcp_params.alpha_beta
            eqd2 = dvh.to_eqd2(n_fractions, alpha_beta)
            return f"{niemierko_geud(eqd2, a=-10.0):.0f}"

        return "--"

    # ------------------------------------------------------------------ #
    def on_accumulate(self):
        from core.dose_accumulation import (
            accumulate_dvh_weighted, accumulate_dvh_simple_sum, PhaseWeight
        )
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        if len(rows) < 2:
            QMessageBox.information(self, "Select 2+ DVHs",
                                     "Select 2 or more DVH rows (same structure, different "
                                     "phases/courses) to accumulate.")
            return
        plan = self.state.active_plan()
        if plan is None:
            return
        dvhs = []
        for r in rows:
            name = self.table.item(r, 0).text()
            dvh = plan.dvhs.get(name)
            if dvh is not None:
                dvhs.append(dvh)
        if len(dvhs) < 2:
            return

        mode, ok = QInputDialog.getItem(
            self, "Accumulation mode", "How should these DVHs combine?",
            ["Sum (sequential courses, e.g. primary + boost)",
             "Weighted average (breathing phases, equal weight)"],
            0, False
        )
        if not ok:
            return

        if mode.startswith("Sum"):
            acc = accumulate_dvh_simple_sum(dvhs)
        else:
            phases = [PhaseWeight(dvh=d, weight=1.0) for d in dvhs]
            acc = accumulate_dvh_weighted(phases)

        new_name, ok = QInputDialog.getText(
            self, "Name accumulated DVH", "Name:",
            text=f"{dvhs[0].structure_name}_accumulated"
        )
        if not ok or not new_name:
            return
        acc.structure_name = new_name
        self._register_dvh(plan, new_name, acc, "computed: dose accumulation", "Accumulated")
        self.refresh_table()
        self.state.dvh_data_changed.emit()

    # ------------------------------------------------------------------ #
    def refresh_table(self):
        self.table.setRowCount(0)
        for entry in self._loaded:
            plan = self.state.plans.get(entry["plan_id"])
            if plan is None or entry["name"] not in plan.dvhs:
                continue
            dvh: DVH = plan.dvhs[entry["name"]]
            assoc = plan.dvh_associations.get(entry["name"], "")
            row = self.table.rowCount()
            self.table.insertRow(row)
            dose_summary = f"{dvh.max_dose_cgy:.0f} / 0 / {dvh.mean_dose_cgy:.0f}"
            eud_str = self._compute_display_eud_cgy(dvh, assoc, plan.fractions)
            values = [
                entry["name"], assoc, entry["type"], entry["file"],
                dose_summary, eud_str, f"{dvh.total_volume_cm3:.1f}",
                entry["plan_id"],
            ]
            for col, v in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(v))
