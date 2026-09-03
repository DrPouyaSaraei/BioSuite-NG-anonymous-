"""
ui/tab_optimisation.py
Mirrors the original "Optimisation" tab: isotoxic optimisation plot
(TCP % vs Number of Fractions), a table of endpoints with their current
NTCP/TCP value and limit, and controls for fraction range / overshoot
limit, reproducing Figures 3-5 of the paper.
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QGridLayout, QInputDialog,
    QMessageBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ui.app_state import AppState
from ui.plot_utils import apply_graph_paper_grid, fix_layout
from core.tcp_models import tcp_lq_poisson_marsden_dvh
from ui.tcp_ntcp_compute import compute_tcp
from core.optimizer import NTCPLimit, optimise_2d_isotoxic


class OptimisationTab(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.fraction_lo, self.fraction_hi = 10, 50
        self.overshoot_tcp = 0.99
        self._build_ui()
        self.state.plans_changed.connect(self.refresh_table)
        self.state.active_plan_changed.connect(lambda _: self.refresh_table())
        self.state.endpoints_changed.connect(self.refresh_table)
        self.state.dvh_data_changed.connect(self.refresh_table)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("Isotoxic optimisation")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        self.fig = Figure(figsize=(6, 3.5))
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Number of fractions")
        self.ax.set_ylabel("TCP (%)")
        fix_layout(self.fig)
        layout.addWidget(self.canvas)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Name", "Endpoint", "Model", "Current NTCP/TCP", "Limit"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        bottom = QHBoxLayout()
        btn_col = QVBoxLayout()
        self.btn_dose = QPushButton("Change prescribed dose")
        self.btn_fxsize = QPushButton("Change fraction size")
        self.btn_range = QPushButton("Change fraction range")
        self.btn_overshoot = QPushButton("Change overshoot limit")
        self.btn_fxnum = QPushButton("Change fraction number")
        for b in [self.btn_dose, self.btn_fxsize, self.btn_range, self.btn_overshoot, self.btn_fxnum]:
            btn_col.addWidget(b)
        bottom.addLayout(btn_col)

        info_grid = QGridLayout()
        info_grid.addWidget(QLabel("Fraction range:"), 0, 0)
        self.range_label = QLabel(f"[{self.fraction_lo};{self.fraction_hi}]")
        info_grid.addWidget(self.range_label, 0, 1)
        info_grid.addWidget(QLabel("Overshoot limit:"), 1, 0)
        self.overshoot_label = QLabel(f"{self.overshoot_tcp*100:.1f}% TCP")
        info_grid.addWidget(self.overshoot_label, 1, 1)
        info_grid.addWidget(QLabel("Best score reached for"), 2, 0, 1, 2)
        info_grid.addWidget(QLabel("Nb of frac.:"), 3, 0)
        self.best_nf_label = QLabel("-")
        info_grid.addWidget(self.best_nf_label, 3, 1)
        info_grid.addWidget(QLabel("Total dose:"), 4, 0)
        self.best_dose_label = QLabel("-")
        info_grid.addWidget(self.best_dose_label, 4, 1)
        info_grid.addWidget(QLabel("Best score:"), 5, 0)
        self.best_score_label = QLabel("-")
        info_grid.addWidget(self.best_score_label, 5, 1)
        bottom.addLayout(info_grid)
        bottom.addStretch()

        layout.addLayout(bottom)

        run_row = QHBoxLayout()
        self.run_btn = QPushButton("Run isotoxic optimisation")
        run_row.addWidget(self.run_btn)
        run_row.addStretch()
        layout.addLayout(run_row)

        self.btn_range.clicked.connect(self.on_change_range)
        self.btn_overshoot.clicked.connect(self.on_change_overshoot)
        self.run_btn.clicked.connect(self.run_optimisation)

    # ------------------------------------------------------------------ #
    def on_change_range(self):
        lo, ok1 = QInputDialog.getInt(self, "Fraction range", "Minimum fractions:", self.fraction_lo, 1, 200)
        if not ok1:
            return
        hi, ok2 = QInputDialog.getInt(self, "Fraction range", "Maximum fractions:", self.fraction_hi, lo, 200)
        if not ok2:
            return
        self.fraction_lo, self.fraction_hi = lo, hi
        self.range_label.setText(f"[{lo};{hi}]")

    def on_change_overshoot(self):
        val, ok = QInputDialog.getDouble(self, "Overshoot limit", "TCP overshoot (%):",
                                          self.overshoot_tcp * 100, 50.0, 99.9, 1)
        if ok:
            self.overshoot_tcp = val / 100.0
            self.overshoot_label.setText(f"{val:.1f}% TCP")

    # ------------------------------------------------------------------ #
    def refresh_table(self):
        self.table.setRowCount(0)
        plan = self.state.active_plan()
        if plan is None:
            return
        for struct_name, ep_name in plan.dvh_associations.items():
            dvh = plan.dvhs.get(struct_name)
            ep = self.state.endpoints.get(ep_name)
            if dvh is None or ep is None:
                continue
            if ep.kind == "NTCP" and ep.ntcp_endpoint is not None:
                current = ep.ntcp_endpoint.compute(dvh, plan.fractions) * 100
            elif ep.kind == "TCP" and ep.tcp_params is not None:
                current = compute_tcp(ep, dvh, plan.fractions) * 100
            else:
                current = 0.0
            row = self.table.rowCount()
            self.table.insertRow(row)
            limit_item = QTableWidgetItem(f"{current:.1f}" if ep.kind == "NTCP" else "")
            if ep.kind == "NTCP":
                limit_item.setFlags(limit_item.flags() | Qt.ItemFlag.ItemIsEditable)
            for col, v in enumerate([struct_name, ep_name, ep.model, f"{current:.2f}%"]):
                self.table.setItem(row, col, QTableWidgetItem(str(v)))
            self.table.setItem(row, 4, limit_item)

    def run_optimisation(self):
        plan = self.state.active_plan()
        if plan is None:
            QMessageBox.warning(self, "No plan", "Select/create a treatment plan first.")
            return

        ntcp_limits = []
        tcp_endpoint = None
        tcp_dvh = None
        for row in range(self.table.rowCount()):
            struct_name = self.table.item(row, 0).text()
            ep_name = self.table.item(row, 1).text()
            ep = self.state.endpoints.get(ep_name)
            dvh = plan.dvhs.get(struct_name)
            if ep is None or dvh is None:
                continue
            if ep.kind == "NTCP":
                try:
                    limit = float(self.table.item(row, 4).text()) / 100.0
                except (ValueError, AttributeError):
                    limit = 1.0
                ntcp_limits.append((NTCPLimit(endpoint=ep.ntcp_endpoint, limit=limit), dvh))
            elif ep.kind == "TCP" and tcp_endpoint is None:
                tcp_endpoint = ep
                tcp_dvh = dvh

        if tcp_endpoint is None or tcp_dvh is None:
            QMessageBox.warning(self, "No TCP endpoint", "Associate a TCP endpoint with a "
                                                          "structure DVH first (Model/Endpoint + DVH import tabs).")
            return

        dvh_by_structure = {lim.endpoint.name: dvh for lim, dvh in ntcp_limits}
        limits_only = [lim for lim, _ in ntcp_limits]
        reference_dose = tcp_dvh.mean_dose_cgy

        def tcp_fn(total_dose_cgy, n_fractions):
            factor = total_dose_cgy / reference_dose if reference_dose > 0 else 1.0
            scaled = tcp_dvh.scale_dose(factor)
            return compute_tcp(tcp_endpoint, scaled, n_fractions)

        try:
            results = optimise_2d_isotoxic(
                fraction_range=range(self.fraction_lo, self.fraction_hi + 1),
                dvh_by_structure=dvh_by_structure,
                ntcp_limits=limits_only,
                tcp_fn=tcp_fn,
                reference_dose_cgy=reference_dose,
                dose_search_range_cgy=(100.0, reference_dose * 3),
                overshoot_tcp=self.overshoot_tcp,
            )
        except Exception as e:
            QMessageBox.critical(self, "Optimisation error", str(e))
            return

        n_fracs = [r.n_fractions for r in results]
        tcps = [r.tcp * 100 for r in results]
        self.ax.clear()
        colors = ["red" if r.limiting_endpoint != "overshoot" else "green" for r in results]
        self.ax.scatter(n_fracs, tcps, c=colors, s=25)
        self.ax.plot(n_fracs, tcps, linewidth=0.7, color="gray")
        self.ax.set_xlabel("Number of fractions")
        self.ax.set_ylabel("TCP (%)")
        self.ax.set_ylim(0, 100)
        apply_graph_paper_grid(self.ax)
        fix_layout(self.fig)
        self.canvas.draw()

        best = max(results, key=lambda r: r.tcp)
        self.best_nf_label.setText(str(best.n_fractions))
        self.best_dose_label.setText(f"{best.total_dose_cgy/100:.1f} Gy")
        self.best_score_label.setText(f"{best.tcp*100:.1f}% TCP")
