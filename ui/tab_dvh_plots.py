"""
ui/tab_dvh_plots.py
Mirrors the original "DVH plots" tab: DVH curves plot, a list of
structures (with checkboxes to show/hide), TCP%/LQ-corrected-NTCP% read-outs
for the currently selected structure+endpoint, and display options
(Normalised, Differential/Cumulative, Uncorrected/LQ-corrected).

Fixes applied per user feedback (screenshots):
  - TCP and NTCP group boxes now share equal width (stretch=1 each)
    instead of TCP being squeezed narrow.
  - Figure uses tight_layout()/subplots_adjust so the x-axis label is
    never clipped at the bottom of the canvas.
  - Chart title changes between "Absolute value DVH(s)" and "Normalized
    DVH(s)" based ONLY on the Normalised radio buttons (not DVH type or
    LQ-correction, per user's explicit instruction).
  - Fine "graph paper" grid (major + minor gridlines) on the plot so
    values can be read off precisely.
  - "Compute 95% CI" now works for ALL NTCP models (LKB, RS, SMD, EUD),
    not just LKB.
  - New "Sensitivity (tornado)" button/plot showing which parameter
    drives the most NTCP uncertainty.
"""
from __future__ import annotations
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton, QListWidget,
    QListWidgetItem, QLabel, QCheckBox, QPushButton, QDialog
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ui.app_state import AppState
from core.dvh import DVH
from core.confidence import ParamUncertainty, monte_carlo_ci, tornado_sensitivity


def _apply_graph_paper_grid(ax):
    """Fine 'graph paper' grid (major + minor) so values can be read off
    the chart precisely, per user request."""
    ax.minorticks_on()
    ax.grid(True, which="major", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.grid(True, which="minor", linestyle=":", linewidth=0.4, alpha=0.35)


class DVHPlotsTab(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self._build_ui()
        self.state.plans_changed.connect(self.refresh)
        self.state.active_plan_changed.connect(lambda _: self.refresh())
        self.state.endpoints_changed.connect(self.refresh)
        self.state.dvh_data_changed.connect(self.refresh)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.fig = Figure(figsize=(6, 3.5))
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Dose (cGy)")
        self.ax.set_ylabel("Volume (%)")
        self.fig.subplots_adjust(bottom=0.16, top=0.90, left=0.11, right=0.97)
        layout.addWidget(self.canvas)

        bottom_row = QHBoxLayout()

        self.struct_list = QListWidget()
        self.struct_list.itemChanged.connect(lambda _: self.plot())
        self.struct_list.currentItemChanged.connect(lambda *_: self.update_readouts())
        bottom_row.addWidget(self.struct_list, stretch=2)

        # --- TCP and NTCP boxes: FORCED equal width. Equal stretch alone
        # was not enough (Qt still grows a box to fit its own widest child
        # row first, and the NTCP box's two side-by-side buttons made it
        # wider than TCP no matter the stretch factor) -- so the two
        # 'compute' buttons now stack vertically (narrower row), AND both
        # boxes get the exact same explicit minimum width below.
        tcp_box = QGroupBox("TCP")
        tcp_layout = QVBoxLayout(tcp_box)
        self.tcp_label = QLabel("--- %")
        self.tcp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tcp_label.setStyleSheet("font-size: 16px;")
        tcp_layout.addWidget(self.tcp_label)
        tcp_layout.addStretch()
        bottom_row.addWidget(tcp_box, stretch=1)

        ntcp_box = QGroupBox("LQ corrected NTCP")
        ntcp_layout = QVBoxLayout(ntcp_box)
        self.ntcp_label = QLabel("--- %")
        self.ntcp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ntcp_label.setStyleSheet("font-size: 16px;")
        ntcp_layout.addWidget(self.ntcp_label)
        self.adjust_frac_chk = QCheckBox("Adjust NTCP for fractionation")
        self.adjust_frac_chk.setChecked(True)
        self.adjust_frac_chk.stateChanged.connect(lambda _: self.update_readouts())
        ntcp_layout.addWidget(self.adjust_frac_chk)
        self.ci_label = QLabel("")
        self.ci_label.setWordWrap(True)
        self.ci_label.setStyleSheet("color: #555; font-size: 10px;")
        self.ci_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ntcp_layout.addWidget(self.ci_label)
        self.ci_btn = QPushButton("Compute 95% CI (Monte-Carlo) [NEW]")
        self.ci_btn.setToolTip(
            "Propagates +/-10% uncertainty on the endpoint's key parameters "
            "through the model (core/confidence.py) -- not in the original BioSuite."
        )
        self.ci_btn.clicked.connect(self.compute_ci)
        self.tornado_btn = QPushButton("Sensitivity (tornado) [NEW]")
        self.tornado_btn.setToolTip(
            "Shows which single parameter drives the most NTCP uncertainty "
            "(core/confidence.py:tornado_sensitivity) -- not in the original BioSuite."
        )
        self.tornado_btn.clicked.connect(self.show_tornado)
        ntcp_layout.addWidget(self.ci_btn)      # stacked vertically now, not side-by-side
        ntcp_layout.addWidget(self.tornado_btn)
        bottom_row.addWidget(ntcp_box, stretch=1)

        # Force identical width regardless of each box's own content: take
        # the wider of the two natural size hints and apply it to BOTH.
        equal_width = max(tcp_box.sizeHint().width(), ntcp_box.sizeHint().width(), 230)
        tcp_box.setMinimumWidth(equal_width)
        ntcp_box.setMinimumWidth(equal_width)

        disp_box = QGroupBox("Display options")
        disp_layout = QVBoxLayout(disp_box)

        norm_box = QGroupBox("Normalised")
        norm_l = QHBoxLayout(norm_box)
        self.norm_no = QRadioButton("No"); self.norm_no.setChecked(True)
        self.norm_yes = QRadioButton("Yes")
        norm_l.addWidget(self.norm_no); norm_l.addWidget(self.norm_yes)
        disp_layout.addWidget(norm_box)

        type_box = QGroupBox("DVH type")
        type_l = QHBoxLayout(type_box)
        self.type_diff = QRadioButton("Differential"); self.type_diff.setChecked(True)
        self.type_cum = QRadioButton("Cumulative")
        type_l.addWidget(self.type_diff); type_l.addWidget(self.type_cum)
        disp_layout.addWidget(type_box)

        lq_box = QGroupBox("Display DVH with LQ correction")
        lq_l = QHBoxLayout(lq_box)
        self.lq_uncorrected = QRadioButton("Uncorrected"); self.lq_uncorrected.setChecked(True)
        self.lq_corrected = QRadioButton("LQ Corrected")
        lq_l.addWidget(self.lq_uncorrected); lq_l.addWidget(self.lq_corrected)
        disp_layout.addWidget(lq_box)

        bottom_row.addWidget(disp_box, stretch=1)
        layout.addLayout(bottom_row)

        for rb in [self.norm_no, self.norm_yes, self.type_diff, self.type_cum,
                   self.lq_uncorrected, self.lq_corrected]:
            rb.toggled.connect(lambda _: self.plot())

    # ------------------------------------------------------------------ #
    def refresh(self):
        plan = self.state.active_plan()
        self.struct_list.blockSignals(True)
        self.struct_list.clear()
        if plan:
            for name in plan.dvhs:
                assoc = plan.dvh_associations.get(name)
                ep = self.state.endpoints.get(assoc) if assoc else None
                label = f"{name} - {assoc} ({ep.model})" if ep else name
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self.struct_list.addItem(item)
        self.struct_list.blockSignals(False)
        self.plot()
        self.update_readouts()

    def _get_display_dvh(self, dvh: DVH) -> DVH:
        n_fractions = self.state.active_plan().fractions if self.state.active_plan() else 1
        out = dvh
        if self.lq_corrected.isChecked():
            out = dvh.to_eqd2(n_fractions, 3.0)  # default a/b=3 for display purposes
        return out

    def plot(self):
        self.ax.clear()
        plan = self.state.active_plan()
        if plan is None:
            self.canvas.draw()
            return
        for i in range(self.struct_list.count()):
            item = self.struct_list.item(i)
            if item.checkState() != Qt.CheckState.Checked:
                continue
            name = item.data(Qt.ItemDataRole.UserRole) or item.text()
            dvh = plan.dvhs.get(name)
            if dvh is None:
                continue
            dvh = self._get_display_dvh(dvh)
            dose = dvh.dose_bins_cgy
            if self.type_cum.isChecked():
                vol = dvh.cumulative_volume_cm3()
            else:
                vol = dvh.volume_cm3
            if self.norm_yes.isChecked() and dvh.total_volume_cm3 > 0:
                vol = vol / dvh.total_volume_cm3 * 100.0
            self.ax.plot(dose, vol, label=name, linewidth=1.4)

        # Title depends ONLY on Normalised Yes/No, per user's explicit request
        # (DVH type and LQ-correction do NOT change the title).
        self.ax.set_title("Normalized DVH(s)" if self.norm_yes.isChecked() else "Absolute value DVH(s)")
        self.ax.set_xlabel("Dose (cGy)")
        self.ax.set_ylabel("Volume (%)" if self.norm_yes.isChecked() else "Volume (cm3)")
        if self.ax.get_legend_handles_labels()[0]:
            self.ax.legend(fontsize=7)
        _apply_graph_paper_grid(self.ax)
        self.fig.subplots_adjust(bottom=0.16, top=0.90, left=0.11, right=0.97)
        self.canvas.draw()

    # ------------------------------------------------------------------ #
    def _current_struct_and_endpoint(self):
        """Resolve the (structure_name, EndpointDefinition, DVH) currently
        selected/highlighted (or the first associated one, as fallback)."""
        plan = self.state.active_plan()
        if plan is None:
            return None, None, None
        current = self.struct_list.currentItem()
        struct_name = current.data(Qt.ItemDataRole.UserRole) if current else None
        if struct_name is None or struct_name not in plan.dvh_associations:
            struct_name = next(iter(plan.dvh_associations), None)
        if struct_name is None:
            return None, None, None
        ep_name = plan.dvh_associations[struct_name]
        ep = self.state.endpoints.get(ep_name)
        dvh = plan.dvhs.get(struct_name)
        return struct_name, ep, dvh

    def _param_uncertainties_for_endpoint(self, ep, rel_sd: float = 0.10):
        """Build a generic +/-`rel_sd` (default 10%) ParamUncertainty list
        for whichever NTCP model this endpoint uses, and a matching
        compute_fn(**params) -> NTCP. Works for LKB, RS, SMD, EUD alike
        (previously only LKB was wired up)."""
        from core.ntcp_models import NTCPEndpoint, LKBParams, RelSerialityParams, SMDParams
        from core.ntcp_niemierko import NiemierkoEUDParams

        model = ep.ntcp_endpoint.model
        base = ep.ntcp_endpoint.params
        alpha_beta = ep.ntcp_endpoint.alpha_beta

        if model == "LKB":
            uncertainties = [
                ParamUncertainty("td50", mean=base.td50, sd=base.td50 * rel_sd, lower_bound=1.0),
                ParamUncertainty("m", mean=base.m, sd=base.m * rel_sd, lower_bound=0.01),
            ]

            def compute(dvh, n_fractions, **kw):
                p = LKBParams(td50=kw["td50"], m=kw["m"], n=base.n, alpha_beta=base.alpha_beta)
                temp = NTCPEndpoint(name=ep.name, model="LKB", alpha_beta=alpha_beta, params=p)
                return temp.compute(dvh, n_fractions)

        elif model == "RS":
            uncertainties = [
                ParamUncertainty("d50", mean=base.d50, sd=base.d50 * rel_sd, lower_bound=1.0),
                ParamUncertainty("gamma50", mean=base.gamma50, sd=base.gamma50 * rel_sd, lower_bound=0.1),
            ]

            def compute(dvh, n_fractions, **kw):
                p = RelSerialityParams(d50=kw["d50"], gamma50=kw["gamma50"], s=base.s)
                temp = NTCPEndpoint(name=ep.name, model="RS", alpha_beta=alpha_beta, params=p)
                return temp.compute(dvh, n_fractions)

        elif model == "SMD":
            uncertainties = [
                ParamUncertainty("d_lim", mean=base.d_lim, sd=base.d_lim * rel_sd, lower_bound=1.0),
            ]

            def compute(dvh, n_fractions, **kw):
                p = SMDParams(d_lim=kw["d_lim"], alpha_beta=base.alpha_beta)
                temp = NTCPEndpoint(name=ep.name, model="SMD", alpha_beta=alpha_beta, params=p)
                return temp.compute(dvh, n_fractions)

        elif model == "EUD":
            uncertainties = [
                ParamUncertainty("td50", mean=base.td50, sd=base.td50 * rel_sd, lower_bound=1.0),
                ParamUncertainty("gamma50", mean=base.gamma50, sd=base.gamma50 * rel_sd, lower_bound=0.1),
            ]

            def compute(dvh, n_fractions, **kw):
                p = NiemierkoEUDParams(a=base.a, td50=kw["td50"], gamma50=kw["gamma50"])
                temp = NTCPEndpoint(name=ep.name, model="EUD", alpha_beta=alpha_beta, params=p)
                return temp.compute(dvh, n_fractions)

        else:
            return None, None

        return uncertainties, compute

    # ------------------------------------------------------------------ #
    def compute_ci(self):
        struct_name, ep, dvh = self._current_struct_and_endpoint()
        if ep is None or dvh is None:
            self.ci_label.setText("(associate an endpoint first)")
            return
        if ep.kind != "NTCP":
            self.ci_label.setText("(CI is currently implemented for NTCP endpoints only)")
            return

        uncertainties, compute = self._param_uncertainties_for_endpoint(ep)
        if uncertainties is None:
            self.ci_label.setText(f"(CI not available for model '{ep.model}')")
            return

        plan = self.state.active_plan()
        result = monte_carlo_ci(
            compute_fn=compute,
            param_uncertainties=uncertainties,
            fixed_kwargs={"dvh": dvh, "n_fractions": plan.fractions},
            n_samples=3000, ci=0.95,
        )
        self.ci_label.setText(
            f"95% CI: [{result['lower']*100:.1f}%, {result['upper']*100:.1f}%]  "
            f"(assumes \u00b110% uncertainty on the model's key parameters)"
        )

    def show_tornado(self):
        struct_name, ep, dvh = self._current_struct_and_endpoint()
        if ep is None or dvh is None or ep.kind != "NTCP":
            self.ci_label.setText("(associate an NTCP endpoint first)")
            return
        uncertainties, compute = self._param_uncertainties_for_endpoint(ep)
        if uncertainties is None:
            self.ci_label.setText(f"(Sensitivity analysis not available for model '{ep.model}')")
            return

        plan = self.state.active_plan()
        result = tornado_sensitivity(
            compute_fn=lambda **kw: compute(dvh=dvh, n_fractions=plan.fractions, **kw),
            param_uncertainties=uncertainties,
            fixed_kwargs={},
        )
        dlg = TornadoDialog(ep.name, result, self)
        dlg.exec()

    def update_readouts(self):
        plan = self.state.active_plan()
        if plan is None:
            self.tcp_label.setText("--- %")
            self.ntcp_label.setText("--- %")
            return

        struct_name, ep, dvh = self._current_struct_and_endpoint()
        if struct_name is None or ep is None or dvh is None:
            self.tcp_label.setText("--- %")
            self.ntcp_label.setText("--- %")
            return

        if ep.kind == "NTCP" and ep.ntcp_endpoint is not None:
            value = ep.ntcp_endpoint.compute(dvh, plan.fractions) * 100
            self.ntcp_label.setText(f"{value:.1f} %")
            self.tcp_label.setText("--- %")
            self.tcp_label.setToolTip("")
        elif ep.kind == "TCP" and ep.tcp_params is not None:
            from ui.tcp_ntcp_compute import compute_tcp
            gtv_vol = ep.gtv_volume_cm3 or dvh.total_volume_cm3
            value = compute_tcp(ep, dvh, plan.fractions) * 100
            self.tcp_label.setText(f"{value:.1f} %")
            self.ntcp_label.setText("--- %")
            if value < 0.05:
                # TCP underflowing to ~0 is usually NOT a bug -- it means the
                # assumed clonogen count (density x volume) is far too large
                # to be sterilised at this dose. Explain WHY instead of just
                # showing a bare "0.0 %".
                total_clonogens = ep.tcp_params.clonogen_density * gtv_vol
                self.tcp_label.setToolTip(
                    f"TCP rounds to ~0% because the assumed clonogen count "
                    f"(density {ep.tcp_params.clonogen_density:.1e}/cc x volume "
                    f"{gtv_vol:.1f}cc = {total_clonogens:.1e} clonogens) is far too "
                    f"large to be sterilised at this dose. This is expected if you "
                    f"applied a TUMOUR clonogen density to a non-tumour structure, or "
                    f"if the dose here is well below a tumoricidal prescription. TCP "
                    f"should normally be computed on the GTV/PTV of an actual target "
                    f"volume, paired with an appropriate clonogen density for that "
                    f"tumour type -- not on an arbitrary OAR/structure DVH."
                )
            else:
                self.tcp_label.setToolTip("")


class TornadoDialog(QDialog):
    """Small pop-up showing a tornado (sensitivity) bar chart for the
    currently-selected NTCP endpoint -- see core/confidence.py:tornado_sensitivity."""

    def __init__(self, endpoint_name: str, result: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Sensitivity analysis -- {endpoint_name}")
        self.resize(560, 380)
        layout = QVBoxLayout(self)

        fig = Figure(figsize=(5.5, 3.6))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        rows = result["rows"]
        names = [r["name"] for r in rows]
        lows = [r["low_output"] * 100 for r in rows]
        highs = [r["high_output"] * 100 for r in rows]
        base = result["base"] * 100
        y_pos = np.arange(len(names))

        for y, lo, hi in zip(y_pos, lows, highs):
            left = min(lo, hi)
            width = abs(hi - lo)
            ax.barh(y, width, left=left, height=0.5, color="#4C72B0", alpha=0.8)

        ax.axvline(base, color="black", linewidth=1, linestyle="--", label=f"base = {base:.1f}%")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(names)
        ax.invert_yaxis()  # largest driver on top
        ax.set_xlabel("NTCP (%)")
        ax.set_title("Tornado sensitivity (\u00b11 SD per parameter)")
        ax.legend(fontsize=8, loc="lower right")
        _apply_graph_paper_grid(ax)
        fig.subplots_adjust(bottom=0.18, top=0.88, left=0.20, right=0.96)

        layout.addWidget(canvas)

        note = QLabel(
            "Each bar spans the NTCP range when ONE parameter is moved \u00b11 SD, "
            "holding all others at their mean. Longer bars = bigger individual driver "
            "of the model's uncertainty."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#555; font-size: 10px;")
        layout.addWidget(note)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
