"""
ui/tab_fitting.py
Mirrors the original "Fitting" tab: data-source table (manual entries of
dose/fractions/volume/outcome), Model = Marsden, Fitting equation =
ChiSq/Binomial/Bernoulli, and a Fit button that reports the fitted alpha.
"""
from __future__ import annotations
import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QLabel,
    QComboBox, QMessageBox, QInputDialog
)

from ui.app_state import AppState
from core.fitting import FitEntry, fit_alpha
from core.tcp_models import TCPParams


class FittingTab(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.entries: list[FitEntry] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        src_box = QGroupBox("Data source")
        src_l = QVBoxLayout(src_box)
        self.src_dvhs = QRadioButton("DVHs")
        self.src_prescription = QRadioButton("Prescription"); self.src_prescription.setChecked(True)
        src_l.addWidget(self.src_dvhs); src_l.addWidget(self.src_prescription)
        top.addWidget(src_box)

        btn_col = QVBoxLayout()
        self.add_manual_btn = QPushButton("Add entry manually")
        fill_row = QHBoxLayout()
        self.fill_outcome_combo = QComboBox()
        self.fill_outcome_combo.addItems(["Random", "All=1 (controlled)", "All=0 (failed)"])
        self.fill_outcome_btn = QPushButton("Fill outcome")
        fill_row.addWidget(self.fill_outcome_combo)
        fill_row.addWidget(self.fill_outcome_btn)
        self.delete_btn = QPushButton("Delete selected entries")
        self.clear_btn = QPushButton("Clear all data")
        btn_col.addWidget(self.add_manual_btn)
        btn_col.addLayout(fill_row)
        btn_col.addWidget(self.delete_btn)
        btn_col.addWidget(self.clear_btn)
        top.addLayout(btn_col)

        model_box = QGroupBox("Model")
        model_l = QVBoxLayout(model_box)
        self.model_list = QListWidget()
        self.model_list.addItem("Marsden")
        self.model_list.setCurrentRow(0)
        model_l.addWidget(self.model_list)
        top.addWidget(model_box)

        eq_box = QGroupBox("Fitting equation")
        eq_l = QVBoxLayout(eq_box)
        self.eq_list = QListWidget()
        self.eq_list.addItems(["ChiSq", "Binomial", "Bernoulli"])
        self.eq_list.setCurrentRow(2)
        eq_l.addWidget(self.eq_list)
        top.addWidget(eq_box)

        fitlist_box = QGroupBox("Fit list")
        fitlist_l = QVBoxLayout(fitlist_box)
        self.fit_list = QListWidget()
        fitlist_l.addWidget(self.fit_list)
        modify_row = QHBoxLayout()
        self.modify_btn = QPushButton("Modify")
        modify_row.addWidget(self.modify_btn)
        fitlist_l.addLayout(modify_row)
        top.addWidget(fitlist_box)

        col_btn_col = QVBoxLayout()
        self.create_fit_btn = QPushButton("Create Fit")
        self.add_col_btn = QPushButton("Add column")
        self.del_col_btn = QPushButton("Delete column")
        self.fit_btn = QPushButton("Fit")
        col_btn_col.addWidget(self.create_fit_btn)
        col_btn_col.addWidget(self.add_col_btn)
        col_btn_col.addWidget(self.del_col_btn)
        col_btn_col.addStretch()
        col_btn_col.addWidget(self.fit_btn)
        top.addLayout(col_btn_col)

        layout.addLayout(top)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Label", "Total dose (cGy)", "Fractions", "Volume (cm3)", "Outcome (0/1)"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        self.result_label = QLabel("")
        layout.addWidget(self.result_label)

        self.add_manual_btn.clicked.connect(self.on_add_manual)
        self.fill_outcome_btn.clicked.connect(self.on_fill_outcome)
        self.delete_btn.clicked.connect(self.on_delete_selected)
        self.clear_btn.clicked.connect(self.on_clear_all)
        self.fit_btn.clicked.connect(self.on_fit)

    # ------------------------------------------------------------------ #
    def on_add_manual(self):
        label, ok = QInputDialog.getText(self, "New entry", "Patient/entry label:")
        if not ok or not label:
            return
        dose, ok = QInputDialog.getDouble(self, "New entry", "Total dose (cGy):", 6000, 0, 20000, 0)
        if not ok:
            return
        fx, ok = QInputDialog.getInt(self, "New entry", "Number of fractions:", 30, 1, 100)
        if not ok:
            return
        vol, ok = QInputDialog.getDouble(self, "New entry", "GTV volume (cm3):", 30.0, 0.1, 2000.0, 1)
        if not ok:
            return
        outcome, ok = QInputDialog.getInt(self, "New entry", "Outcome (1=controlled, 0=failed):", 1, 0, 1)
        if not ok:
            return
        self.entries.append(FitEntry(label=label, total_dose_cgy=dose, n_fractions=fx,
                                      volume_cm3=vol, outcome=outcome))
        self.refresh_table()

    def on_fill_outcome(self):
        mode = self.fill_outcome_combo.currentText()
        for e in self.entries:
            if mode.startswith("Random"):
                e.outcome = random.randint(0, 1)
            elif "1" in mode:
                e.outcome = 1
            else:
                e.outcome = 0
        self.refresh_table()

    def on_delete_selected(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            if 0 <= r < len(self.entries):
                del self.entries[r]
        self.refresh_table()

    def on_clear_all(self):
        self.entries.clear()
        self.refresh_table()

    def refresh_table(self):
        self.table.setRowCount(0)
        for e in self.entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [e.label, f"{e.total_dose_cgy:.0f}", str(e.n_fractions),
                      f"{e.volume_cm3:.1f}", str(e.outcome)]
            for col, v in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(v))

    # ------------------------------------------------------------------ #
    def on_fit(self):
        if not self.entries:
            QMessageBox.information(self, "No data", "Add at least one entry first.")
            return
        equation = self.eq_list.currentItem().text() if self.eq_list.currentItem() else "Bernoulli"
        # base TCPParams: reasonable NSCLC-like defaults; alpha_beta/spread/density
        # fixed, only alpha is fitted (see core/fitting.py docstring)
        base_params = TCPParams(alpha=0.3, alpha_beta=10.0, alpha_spread=0.05, clonogen_density=1e7)
        try:
            result = fit_alpha(self.entries, base_params, equation=equation)
        except Exception as e:
            QMessageBox.critical(self, "Fit error", str(e))
            return
        self.result_label.setText(
            f"Fitted alpha = {result.fitted_alpha:.4f} Gy^-1   "
            f"({equation} score = {result.neg_log_likelihood:.3f}, n={result.n_entries})"
        )
        self.fit_list.addItem(
            f"alpha={result.fitted_alpha:.4f}  [{equation}]  score={result.neg_log_likelihood:.3f}"
        )
