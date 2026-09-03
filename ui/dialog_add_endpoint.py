"""
ui/dialog_add_endpoint.py
Dialog for adding a new NTCP or TCP endpoint, with parameter fields that
change dynamically based on the selected model -- used by the
Model/Endpoint parameters tab's "Add new endpoint" button.
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QLabel, QVBoxLayout
)

from core.ntcp_models import LKBParams, RelSerialityParams, SMDParams, NTCPEndpoint
from core.ntcp_niemierko import NiemierkoEUDParams
from core.tcp_models import TCPParams, LQSLRExtra
from ui.app_state import EndpointDefinition

NTCP_MODELS = ["LKB", "RS (Relative Seriality)", "SMD (Simple Max Dose)", "EUD (Niemierko) [NEW]"]
TCP_MODELS = ["Marsden (LQ-Poisson)", "LQ-SLR"]

MODEL_PARAM_FIELDS = {
    "LKB": [("td50", "TD50 (cGy, EQD2)"), ("m", "m"), ("n", "n"), ("alpha_beta", "alpha/beta (Gy)")],
    "RS (Relative Seriality)": [("d50", "D50 (cGy, EQD2)"), ("gamma50", "gamma50"),
                                 ("s", "s (seriality, 0-1)"), ("alpha_beta", "alpha/beta (Gy)")],
    "SMD (Simple Max Dose)": [("d_lim", "Dlim (cGy, EQD2)"), ("alpha_beta", "alpha/beta (Gy)")],
    "EUD (Niemierko) [NEW]": [("a", "a (volume param)"), ("td50", "TD50 (cGy, EQD2)"),
                                ("gamma50", "gamma50"), ("alpha_beta", "alpha/beta (Gy)")],
    "Marsden (LQ-Poisson)": [("alpha", "alpha (Gy^-1)"), ("alpha_beta", "alpha/beta (Gy)"),
                               ("alpha_spread", "alpha spread (Gy^-1)"),
                               ("clonogen_density", "Clonogen density (cm^-3)"),
                               ("repopulation_delay_days", "Repop. delay (days)"),
                               ("clonogen_doubling_time_days", "Doubling time (days)")],
    "LQ-SLR": [("alpha", "alpha (Gy^-1)"), ("alpha_beta", "alpha/beta (Gy)"),
                ("alpha_spread", "alpha spread (Gy^-1)"),
                ("clonogen_density", "Clonogen density (cm^-3)"),
                ("mu_repair_per_hour", "Repair rate mu (h^-1)"),
                ("fraction_delivery_min", "Delivery time/fraction (min)")],
}

DEFAULTS = {
    "td50": "9770", "m": "0.27", "n": "0.085", "alpha_beta": "3.0",
    "d50": "8000", "gamma50": "2.0", "s": "0.5",
    "d_lim": "8300",
    "a": "1.0",
    "alpha": "0.3", "alpha_spread": "0.1", "clonogen_density": "1e7",
    "repopulation_delay_days": "0", "clonogen_doubling_time_days": "1e9",
    "mu_repair_per_hour": "0.462", "fraction_delivery_min": "2.0",
}


class AddEndpointDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add new endpoint")
        self.result_endpoint: EndpointDefinition | None = None

        self.layout_main = QVBoxLayout(self)
        self.form = QFormLayout()

        self.name_edit = QLineEdit()
        self.kind_combo = QComboBox()
        self.kind_combo.addItems(["NTCP", "TCP"])
        self.model_combo = QComboBox()

        self.form.addRow("Endpoint name:", self.name_edit)
        self.form.addRow("Kind:", self.kind_combo)
        self.form.addRow("Model:", self.model_combo)
        self.layout_main.addLayout(self.form)

        self.param_form = QFormLayout()
        self.layout_main.addLayout(self.param_form)
        self.param_edits: dict[str, QLineEdit] = {}

        self.gtv_vol_edit = QLineEdit()
        self.gtv_vol_row_label = QLabel("GTV volume (cm^3):")
        self.param_form.addRow(self.gtv_vol_row_label, self.gtv_vol_edit)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.layout_main.addWidget(self.buttons)

        self.kind_combo.currentTextChanged.connect(self._on_kind_changed)
        self.model_combo.currentTextChanged.connect(self._rebuild_param_fields)
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)

        self._on_kind_changed("NTCP")

    def _on_kind_changed(self, kind: str):
        self.model_combo.clear()
        self.model_combo.addItems(NTCP_MODELS if kind == "NTCP" else TCP_MODELS)
        self._rebuild_param_fields()

    def _rebuild_param_fields(self):
        # clear old rows (keep GTV row, hidden/shown depending on kind)
        while self.param_form.rowCount() > 0:
            self.param_form.removeRow(0)
        self.param_edits.clear()

        model = self.model_combo.currentText()
        for key, label in MODEL_PARAM_FIELDS.get(model, []):
            edit = QLineEdit(DEFAULTS.get(key, ""))
            self.param_edits[key] = edit
            self.param_form.addRow(label, edit)

        if self.kind_combo.currentText() == "TCP":
            self.gtv_vol_edit = QLineEdit("30.0")
            self.param_form.addRow("GTV volume (cm^3):", self.gtv_vol_edit)

    def _on_accept(self):
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setFocus()
            return
        kind = self.kind_combo.currentText()
        model_label = self.model_combo.currentText()
        try:
            values = {k: float(e.text()) for k, e in self.param_edits.items()}
        except ValueError:
            return  # invalid numeric input; silently keep dialog open

        if kind == "NTCP":
            if model_label == "LKB":
                params = LKBParams(**values)
                model_key = "LKB"
            elif model_label.startswith("RS"):
                params = RelSerialityParams(d50=values["d50"], gamma50=values["gamma50"], s=values["s"])
                model_key = "RS"
            elif model_label.startswith("SMD"):
                params = SMDParams(d_lim=values["d_lim"], alpha_beta=values["alpha_beta"])
                model_key = "SMD"
            else:  # EUD
                params = NiemierkoEUDParams(a=values["a"], td50=values["td50"], gamma50=values["gamma50"])
                model_key = "EUD"
            ntcp_ep = NTCPEndpoint(name=name, model=model_key,
                                    alpha_beta=values.get("alpha_beta", 3.0), params=params)
            self.result_endpoint = EndpointDefinition(
                name=name, kind="NTCP", model=model_key, ntcp_endpoint=ntcp_ep
            )
        else:
            tcp_params = TCPParams(
                alpha=values["alpha"], alpha_beta=values["alpha_beta"],
                alpha_spread=values["alpha_spread"], clonogen_density=values["clonogen_density"],
                repopulation_delay_days=values.get("repopulation_delay_days", 0.0),
                clonogen_doubling_time_days=values.get("clonogen_doubling_time_days", float("inf")),
            )
            try:
                gtv_vol = float(self.gtv_vol_edit.text())
            except ValueError:
                gtv_vol = 30.0

            # FIX: mu_repair_per_hour and fraction_delivery_min were being
            # read into `values` above but then silently discarded here --
            # every "LQ-SLR" endpoint actually computed as plain Marsden.
            lq_slr_extra = None
            if model_label == "LQ-SLR" and "mu_repair_per_hour" in values and "fraction_delivery_min" in values:
                lq_slr_extra = LQSLRExtra(
                    mu_repair_per_hour=values["mu_repair_per_hour"],
                    fraction_delivery_min=values["fraction_delivery_min"],
                )

            self.result_endpoint = EndpointDefinition(
                name=name, kind="TCP", model=model_label, tcp_params=tcp_params,
                gtv_volume_cm3=gtv_vol, lq_slr_extra=lq_slr_extra,
            )
        self.accept()
