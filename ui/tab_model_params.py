"""
ui/tab_model_params.py
Mirrors the original "Model/Endpoint parameters" tab:
  Endpoint combo / Model combo / Add new endpoint / Delete endpoint buttons
  Load list / Save list buttons (persist the endpoint set as JSON)
Adds a summary table (not in the original screenshot, but useful) listing
all currently-defined endpoints and their key parameters, plus a
"Load default bank" button that loads data/default_endpoints.json --
a starter set of organ/LKB parameters, ready to be replaced/extended once
the user supplies their full parameter bank.
"""
from __future__ import annotations
import json
import os
import dataclasses
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox
)

from ui.app_state import AppState, EndpointDefinition
from ui.dialog_add_endpoint import AddEndpointDialog
from ui.dialog_add_from_bank import AddFromBankDialog
from ui.dialog_add_tcp_from_bank import AddTCPFromBankDialog
from core.ntcp_models import NTCPEndpoint, LKBParams, RelSerialityParams, SMDParams
from core.ntcp_niemierko import NiemierkoEUDParams
from core.tcp_models import TCPParams

from core.paths import resource_path

DEFAULT_BANK_PATH = resource_path("data", "default_endpoints.json")


class ModelEndpointTab(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self._build_ui()
        self.state.endpoints_changed.connect(self.refresh)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        form_row = QHBoxLayout()
        form = QFormLayout()
        self.endpoint_combo = QComboBox()
        self.model_combo = QComboBox()
        form.addRow("Endpoint:", self.endpoint_combo)
        form.addRow("Model:", self.model_combo)
        form_row.addLayout(form)

        btn_col = QVBoxLayout()
        self.add_btn = QPushButton("Add new endpoint")
        self.add_from_bank_btn = QPushButton("Add from LKB parameter bank [NEW]")
        self.add_from_bank_btn.setToolTip(
            "Pick Organ \u2192 Endpoint \u2192 Author/Year from a curated, literature-sourced "
            "LKB parameter bank (88 parameter sets across 51 organs)."
        )
        self.add_tcp_from_bank_btn = QPushButton("Add from TCP parameter bank [NEW]")
        self.add_tcp_from_bank_btn.setToolTip(
            "Pick Tumour site \u2192 Endpoint \u2192 Author/Year from a curated Target/Poisson "
            "TCP parameter bank (14 parameter sets across 9 tumour sites)."
        )
        self.delete_btn = QPushButton("Delete endpoint")
        btn_col.addWidget(self.add_btn)
        btn_col.addWidget(self.add_from_bank_btn)
        btn_col.addWidget(self.add_tcp_from_bank_btn)
        btn_col.addWidget(self.delete_btn)
        form_row.addLayout(btn_col)

        io_col = QVBoxLayout()
        self.load_btn = QPushButton("Load list")
        self.save_btn = QPushButton("Save list")
        self.load_default_btn = QPushButton("Load default bank")
        self.load_default_btn.setToolTip(
            "Loads data/default_endpoints.json -- a starter set of organs "
            "(Lung, Rectum, Oesophagus) with literature LKB/SMD parameters. "
            "Replace this file with your own parameter bank at any time."
        )
        io_col.addWidget(self.load_btn)
        io_col.addWidget(self.save_btn)
        io_col.addWidget(self.load_default_btn)
        form_row.addLayout(io_col)
        form_row.addStretch()

        layout.addLayout(form_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Endpoint", "Kind", "Model", "Key parameters"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.table)

        self.add_btn.clicked.connect(self.on_add)
        self.add_from_bank_btn.clicked.connect(self.on_add_from_bank)
        self.add_tcp_from_bank_btn.clicked.connect(self.on_add_tcp_from_bank)
        self.delete_btn.clicked.connect(self.on_delete)
        self.load_btn.clicked.connect(self.on_load_list)
        self.save_btn.clicked.connect(self.on_save_list)
        self.load_default_btn.clicked.connect(self.on_load_default_bank)
        self.endpoint_combo.currentTextChanged.connect(self._sync_model_combo)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)

    def _sync_model_combo(self, name: str):
        ep = self.state.endpoints.get(name)
        self.model_combo.clear()
        if ep:
            self.model_combo.addItem(ep.model)

    # ------------------------------------------------------------------ #
    def on_add(self):
        dlg = AddEndpointDialog(self)
        if dlg.exec():
            if dlg.result_endpoint:
                self.state.add_endpoint(dlg.result_endpoint)

    def on_add_from_bank(self):
        dlg = AddFromBankDialog(self)
        if dlg.exec():
            if dlg.result_endpoint:
                self.state.add_endpoint(dlg.result_endpoint)

    def on_add_tcp_from_bank(self):
        dlg = AddTCPFromBankDialog(self)
        if dlg.exec():
            if dlg.result_endpoint:
                self.state.add_endpoint(dlg.result_endpoint)

    def _on_table_selection_changed(self):
        """Keep the Endpoint combo in sync with whichever row is actually
        highlighted in the table, so 'currentText()' reflects what the
        user visually selected."""
        row = self.table.currentRow()
        if row < 0:
            return
        name_item = self.table.item(row, 0)
        if name_item is None:
            return
        name = name_item.text()
        if name in self.state.endpoints:
            self.endpoint_combo.blockSignals(True)
            self.endpoint_combo.setCurrentText(name)
            self.endpoint_combo.blockSignals(False)
            self._sync_model_combo(name)

    def on_delete(self):
        # FIX: this used to always read self.endpoint_combo.currentText(),
        # which does NOT track which row the user actually clicked/selected
        # in the table -- it silently deleted whatever the combo happened
        # to be showing (typically the first endpoint alphabetically),
        # regardless of the visible table selection. Now reads the
        # table's own selection first, matching what the user actually
        # clicked; falls back to the combo only if no row is selected.
        row = self.table.currentRow()
        name = None
        if row >= 0:
            name_item = self.table.item(row, 0)
            if name_item is not None:
                name = name_item.text()
        if name is None:
            name = self.endpoint_combo.currentText()
        if name:
            self.state.delete_endpoint(name)

    # ------------------------------------------------------------------ #
    def _endpoint_to_dict(self, ep: EndpointDefinition) -> dict:
        d = {"name": ep.name, "kind": ep.kind, "model": ep.model}
        if ep.kind == "NTCP" and ep.ntcp_endpoint is not None:
            d["alpha_beta"] = ep.ntcp_endpoint.alpha_beta
            d["params"] = dataclasses.asdict(ep.ntcp_endpoint.params)
        elif ep.kind == "TCP" and ep.tcp_params is not None:
            d["params"] = dataclasses.asdict(ep.tcp_params)
            d["gtv_volume_cm3"] = ep.gtv_volume_cm3
        return d

    def _dict_to_endpoint(self, d: dict) -> EndpointDefinition:
        if d["kind"] == "NTCP":
            model = d["model"]
            params_cls = {"LKB": LKBParams, "RS": RelSerialityParams,
                           "SMD": SMDParams, "EUD": NiemierkoEUDParams}[model]
            params = params_cls(**d["params"])
            ntcp_ep = NTCPEndpoint(name=d["name"], model=model,
                                    alpha_beta=d.get("alpha_beta", 3.0), params=params)
            return EndpointDefinition(name=d["name"], kind="NTCP", model=model, ntcp_endpoint=ntcp_ep)
        else:
            params = TCPParams(**d["params"])
            return EndpointDefinition(name=d["name"], kind="TCP", model=d["model"],
                                       tcp_params=params, gtv_volume_cm3=d.get("gtv_volume_cm3"))

    def on_save_list(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save endpoint list", "endpoints.json",
                                               "JSON files (*.json)")
        if not path:
            return
        data = [self._endpoint_to_dict(ep) for ep in self.state.endpoints.values()]
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Save error", str(e))

    def on_load_default_bank(self):
        if not os.path.exists(DEFAULT_BANK_PATH):
            QMessageBox.information(self, "Not found",
                                     f"{DEFAULT_BANK_PATH} does not exist.")
            return
        try:
            with open(DEFAULT_BANK_PATH) as f:
                data = json.load(f)
            for d in data:
                self.state.add_endpoint(self._dict_to_endpoint(d))
            QMessageBox.information(self, "Default bank loaded",
                                     f"Loaded {len(data)} endpoint(s) from the default bank.")
        except Exception as e:
            QMessageBox.critical(self, "Load error", str(e))

    def on_load_list(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load endpoint list", "", "JSON files (*.json)")
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
            for d in data:
                self.state.add_endpoint(self._dict_to_endpoint(d))
        except Exception as e:
            QMessageBox.critical(self, "Load error", str(e))

    # ------------------------------------------------------------------ #
    def refresh(self):
        self.endpoint_combo.blockSignals(True)
        current = self.endpoint_combo.currentText()
        self.endpoint_combo.clear()
        self.endpoint_combo.addItems(sorted(self.state.endpoints.keys()))
        if current in self.state.endpoints:
            self.endpoint_combo.setCurrentText(current)
        self.endpoint_combo.blockSignals(False)
        self._sync_model_combo(self.endpoint_combo.currentText())

        self.table.setRowCount(0)
        for ep in self.state.endpoints.values():
            row = self.table.rowCount()
            self.table.insertRow(row)
            if ep.kind == "NTCP" and ep.ntcp_endpoint is not None:
                params_str = ", ".join(f"{k}={v:.3g}" for k, v in
                                        dataclasses.asdict(ep.ntcp_endpoint.params).items())
            elif ep.tcp_params is not None:
                params_str = ", ".join(f"{k}={v:.3g}" for k, v in
                                        dataclasses.asdict(ep.tcp_params).items())
            else:
                params_str = ""
            for col, v in enumerate([ep.name, ep.kind, ep.model, params_str]):
                self.table.setItem(row, col, QTableWidgetItem(str(v)))
