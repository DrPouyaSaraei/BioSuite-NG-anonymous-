"""
ui/tab_treatment_plans.py
Mirrors the original BioSuite "Treatment plans" tab layout:
  - top row of fields: Plan identifier / Fractions / Prescription dose (cGy) /
    Fraction(s)/day / Fractions/week / Fraction delivery duration (min)
  - Add plan / Delete plan / Modify buttons
  - table listing all plans
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt

from ui.app_state import AppState, TreatmentPlan


class TreatmentPlansTab(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self._build_ui()
        self.state.plans_changed.connect(self.refresh_table)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # --- input row ---
        form_row = QHBoxLayout()

        self.plan_id_edit = QLineEdit()
        self.plan_id_edit.setPlaceholderText("Plan identifier")
        self.fractions_edit = QLineEdit()
        self.fractions_edit.setPlaceholderText("Fractions")
        self.dose_edit = QLineEdit()
        self.dose_edit.setPlaceholderText("Prescription dose (cGy)")
        self.frac_per_day = QComboBox()
        self.frac_per_day.addItems([str(i) for i in range(1, 4)])
        self.frac_per_week = QComboBox()
        self.frac_per_week.addItems([str(i) for i in range(1, 8)])
        self.frac_per_week.setCurrentText("5")
        self.delivery_min_edit = QLineEdit()
        self.delivery_min_edit.setPlaceholderText("Fraction delivery duration (min)")
        self.delivery_min_edit.setText("2.0")

        for w, label in [
            (self.plan_id_edit, "Plan identifier"),
            (self.fractions_edit, "Fractions"),
            (self.dose_edit, "Prescription dose (cGy)"),
            (self.frac_per_day, "Fraction(s)/day"),
            (self.frac_per_week, "Fractions/week"),
        ]:
            col = QVBoxLayout()
            col.addWidget(w)
            from PyQt6.QtWidgets import QLabel
            lab = QLabel(label)
            lab.setStyleSheet("font-size: 10px; color: #444;")
            col.addWidget(lab)
            form_row.addLayout(col)

        layout.addLayout(form_row)

        delivery_row = QHBoxLayout()
        delivery_row.addWidget(self.delivery_min_edit)
        from PyQt6.QtWidgets import QLabel
        delivery_row.addWidget(QLabel("Fraction delivery duration (min)"))
        delivery_row.addStretch()
        layout.addLayout(delivery_row)

        # --- buttons ---
        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Add plan")
        self.delete_btn = QPushButton("Delete plan")
        self.modify_btn = QPushButton("Modify")
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addWidget(self.modify_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.add_btn.clicked.connect(self.on_add_plan)
        self.delete_btn.clicked.connect(self.on_delete_plan)
        self.modify_btn.clicked.connect(self.on_modify_plan)

        # --- table ---
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Plan identifier", "Fractions", "Prescription dose (cGy)",
            "Frac/day", "Frac/week", "Length (days)", "Delivery duration (min)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        layout.addWidget(self.table)

    # ------------------------------------------------------------------ #
    def _read_form(self) -> TreatmentPlan | None:
        pid = self.plan_id_edit.text().strip()
        if not pid:
            QMessageBox.warning(self, "Missing data", "Plan identifier is required.")
            return None
        try:
            fractions = int(self.fractions_edit.text())
            dose = float(self.dose_edit.text())
            delivery = float(self.delivery_min_edit.text() or 2.0)
        except ValueError:
            QMessageBox.warning(self, "Invalid data", "Fractions/Dose/Delivery must be numeric.")
            return None
        return TreatmentPlan(
            plan_id=pid, fractions=fractions, prescription_dose_cgy=dose,
            fractions_per_day=int(self.frac_per_day.currentText()),
            fractions_per_week=int(self.frac_per_week.currentText()),
            fraction_delivery_min=delivery,
        )

    def on_add_plan(self):
        plan = self._read_form()
        if plan is None:
            return
        if plan.plan_id in self.state.plans:
            QMessageBox.warning(self, "Duplicate", f"Plan '{plan.plan_id}' already exists.")
            return
        self.state.add_plan(plan)

    def on_modify_plan(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "No selection", "Select a plan row to modify first.")
            return
        old_id = self.table.item(row, 0).text()
        plan = self._read_form()
        if plan is None:
            return
        # preserve any already-imported DVHs when modifying
        if old_id in self.state.plans:
            plan.dvhs = self.state.plans[old_id].dvhs
            plan.dvh_associations = self.state.plans[old_id].dvh_associations
            del self.state.plans[old_id]
        self.state.add_plan(plan)

    def on_delete_plan(self):
        row = self.table.currentRow()
        if row < 0:
            return
        pid = self.table.item(row, 0).text()
        self.state.delete_plan(pid)

    def on_row_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        pid = self.table.item(row, 0).text()
        plan = self.state.plans.get(pid)
        if not plan:
            return
        self.plan_id_edit.setText(plan.plan_id)
        self.fractions_edit.setText(str(plan.fractions))
        self.dose_edit.setText(str(plan.prescription_dose_cgy))
        self.frac_per_day.setCurrentText(str(plan.fractions_per_day))
        self.frac_per_week.setCurrentText(str(plan.fractions_per_week))
        self.delivery_min_edit.setText(str(plan.fraction_delivery_min))
        self.state.set_active_plan(pid)

    def refresh_table(self):
        self.table.setRowCount(0)
        for plan in self.state.plans.values():
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                plan.plan_id, str(plan.fractions), f"{plan.prescription_dose_cgy:.0f}",
                str(plan.fractions_per_day), str(plan.fractions_per_week),
                f"{plan.length_days:.1f}", f"{plan.fraction_delivery_min:.1f}",
            ]
            for col, v in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(v))
