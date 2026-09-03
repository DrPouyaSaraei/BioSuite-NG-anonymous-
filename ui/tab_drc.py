"""
ui/tab_drc.py
Mirrors the original "Dose response curves" tab: plots TCP/NTCP (%) vs a
dose-multiplication factor (constant fraction NUMBER) or vs number of
fractions (constant fraction SIZE) -- reproducing Figures 1 & 2 of the
paper.
"""
from __future__ import annotations
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton, QLabel,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ui.app_state import AppState
from ui.plot_utils import apply_graph_paper_grid, fix_layout
from core.tcp_models import tcp_lq_poisson_marsden_dvh
from ui.tcp_ntcp_compute import compute_tcp


class DRCTab(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self._build_ui()
        self.state.plans_changed.connect(self.refresh_struct_list)
        self.state.active_plan_changed.connect(lambda _: self.refresh_struct_list())
        self.state.endpoints_changed.connect(self.refresh_struct_list)
        self.state.dvh_data_changed.connect(self.refresh_struct_list)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("Dose response curve")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        self.fig = Figure(figsize=(6, 3.5))
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_ylabel("Biological evaluation (%)")
        fix_layout(self.fig)
        layout.addWidget(self.canvas)

        bottom = QHBoxLayout()

        const_box = QGroupBox("Constant...")
        const_l = QVBoxLayout(const_box)
        self.const_size = QRadioButton("Fraction size")
        self.const_number = QRadioButton("Fraction No.")
        self.const_number.setChecked(True)
        const_l.addWidget(self.const_size)
        const_l.addWidget(self.const_number)
        bottom.addWidget(const_box)

        self.struct_list = QListWidget()
        bottom.addWidget(self.struct_list, stretch=2)

        filter_box = QGroupBox("Filter curves")
        filter_l = QVBoxLayout(filter_box)
        self.filter_both = QRadioButton("TCPs & NTCPs"); self.filter_both.setChecked(True)
        self.filter_tcp = QRadioButton("TCPs only")
        self.filter_ntcp = QRadioButton("NTCPs only")
        filter_l.addWidget(self.filter_both)
        filter_l.addWidget(self.filter_tcp)
        filter_l.addWidget(self.filter_ntcp)

        range_row = QHBoxLayout()
        self.max_frac_edit = QLineEdit("50")
        self.min_frac_edit = QLineEdit("10")
        range_row.addWidget(QLabel("Max frac.")); range_row.addWidget(self.max_frac_edit)
        range_row.addWidget(QLabel("Min frac.")); range_row.addWidget(self.min_frac_edit)
        filter_l.addLayout(range_row)
        bottom.addWidget(filter_box)

        layout.addLayout(bottom)

        btn_row = QHBoxLayout()
        self.compute_btn = QPushButton("Compute curves")
        btn_row.addWidget(self.compute_btn)
        btn_row.addStretch()
        self.cursor_label = QLabel("Dose cursor:  0 cGy")
        btn_row.addWidget(self.cursor_label)
        layout.addLayout(btn_row)

        self.compute_btn.clicked.connect(self.compute_and_plot)
        self.canvas.mpl_connect("motion_notify_event", self._on_hover)

    # ------------------------------------------------------------------ #
    def refresh_struct_list(self):
        plan = self.state.active_plan()
        self.struct_list.clear()
        if not plan:
            return
        for name, ep_name in plan.dvh_associations.items():
            item = QListWidgetItem(f"{name}  ->  {ep_name}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, (name, ep_name))
            self.struct_list.addItem(item)

    def _on_hover(self, event):
        if event.xdata is not None:
            self.cursor_label.setText(f"Dose cursor:  x={event.xdata:.2f}  y={event.ydata:.1f}%")

    # ------------------------------------------------------------------ #
    def compute_and_plot(self):
        self.ax.clear()
        plan = self.state.active_plan()
        if plan is None:
            self.canvas.draw()
            return

        constant_number = self.const_number.isChecked()
        if constant_number:
            factors = np.linspace(0.0, 3.0, 61)
            x_label = "Dose multiplication factor (for constant fraction number)"
        else:
            try:
                lo = int(self.min_frac_edit.text())
                hi = int(self.max_frac_edit.text())
            except ValueError:
                lo, hi = 10, 50
            fractions_range = np.arange(max(1, lo), max(hi, lo) + 1)
            x_label = "Number of fractions (constant fraction size)"

        for i in range(self.struct_list.count()):
            item = self.struct_list.item(i)
            if item.checkState() != Qt.CheckState.Checked:
                continue
            struct_name, ep_name = item.data(Qt.ItemDataRole.UserRole)
            dvh = plan.dvhs.get(struct_name)
            ep = self.state.endpoints.get(ep_name)
            if dvh is None or ep is None:
                continue
            if ep.kind == "TCP" and self.filter_ntcp.isChecked():
                continue
            if ep.kind == "NTCP" and self.filter_tcp.isChecked():
                continue

            if constant_number:
                x_vals = factors
                y_vals = []
                for f in factors:
                    scaled = dvh.scale_dose(f)
                    y_vals.append(self._evaluate(ep, scaled, plan.fractions))
            else:
                x_vals = fractions_range
                y_vals = []
                base_total_dose = dvh.mean_dose_cgy  # anchor: treat current mean as "reference" total
                for nf in fractions_range:
                    # constant fraction SIZE: total dose scales with nf, at fixed dose/fraction
                    dose_per_fx = plan.prescription_dose_cgy / plan.fractions
                    factor = (dose_per_fx * nf) / base_total_dose if base_total_dose > 0 else 1.0
                    scaled = dvh.scale_dose(factor)
                    y_vals.append(self._evaluate(ep, scaled, int(nf)))

            label = f"{struct_name} ({ep.kind})"
            self.ax.plot(x_vals, np.array(y_vals) * 100, label=label)

        self.ax.set_xlabel(x_label)
        self.ax.set_ylabel("Biological evaluation (%)")
        self.ax.set_ylim(0, 100)
        if self.ax.get_legend_handles_labels()[0]:
            self.ax.legend(fontsize=7)
        apply_graph_paper_grid(self.ax)
        fix_layout(self.fig)
        self.canvas.draw()

    def _evaluate(self, ep, dvh, n_fractions: int) -> float:
        if ep.kind == "NTCP" and ep.ntcp_endpoint is not None:
            return ep.ntcp_endpoint.compute(dvh, n_fractions)
        elif ep.kind == "TCP" and ep.tcp_params is not None:
            return compute_tcp(ep, dvh, n_fractions)
        return 0.0
