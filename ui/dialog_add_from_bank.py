"""
ui/dialog_add_from_bank.py
Lets the user add a new NTCP (LKB) endpoint by picking Organ -> Endpoint
-> parameter set (by "Author et al. Year"), from the curated LKB
parameter bank (core/lkb_bank.py). If the chosen parameter set's source
did not report alpha/beta, the user is warned and REQUIRED to type one in
before the endpoint can be added (never silently defaulted).
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QLabel, QLineEdit,
    QDialogButtonBox, QTextBrowser, QMessageBox
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

from core.lkb_bank import load_bank, get_organs, get_endpoints, get_parameter_sets
from core.ntcp_models import NTCPEndpoint, LKBParams
from ui.app_state import EndpointDefinition
from ui.combo_utils import enable_typeahead_search


class AddFromBankDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add endpoint from LKB parameter bank")
        self.setMinimumWidth(620)
        self.result_endpoint: EndpointDefinition | None = None
        self._entries = load_bank()
        self._current_entry = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.organ_combo = QComboBox()
        self.organ_combo.addItems(get_organs(self._entries))
        enable_typeahead_search(self.organ_combo)  # type "r" -> jumps to "Rectum", case-insensitive
        self.endpoint_combo = QComboBox()
        enable_typeahead_search(self.endpoint_combo)
        self.author_combo = QComboBox()

        form.addRow("Organ:", self.organ_combo)
        form.addRow("Endpoint:", self.endpoint_combo)
        form.addRow("Parameter set (author, year):", self.author_combo)
        layout.addLayout(form)

        self.detail_view = QTextBrowser()
        self.detail_view.setMinimumHeight(170)
        layout.addWidget(self.detail_view)

        self.warning_label = QLabel("")
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet("color: #b00000; font-weight: bold;")
        layout.addWidget(self.warning_label)

        ab_row = QFormLayout()
        self.alpha_beta_edit = QLineEdit()
        self.alpha_beta_edit.setPlaceholderText("required -- e.g. 3.0")
        ab_row.addRow("alpha/beta (Gy) to use:", self.alpha_beta_edit)
        layout.addLayout(ab_row)

        self.name_edit = QLineEdit()
        name_row = QFormLayout()
        name_row.addRow("Endpoint name in this project:", self.name_edit)
        layout.addLayout(name_row)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(self.buttons)

        self.organ_combo.currentTextChanged.connect(self._on_organ_changed)
        self.endpoint_combo.currentTextChanged.connect(self._on_endpoint_changed)
        self.author_combo.currentTextChanged.connect(self._on_author_changed)
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)

        self._on_organ_changed(self.organ_combo.currentText())

    # ------------------------------------------------------------------ #
    def _on_organ_changed(self, organ: str):
        self.endpoint_combo.blockSignals(True)
        self.endpoint_combo.clear()
        self.endpoint_combo.addItems(get_endpoints(organ, self._entries))
        self.endpoint_combo.blockSignals(False)
        self._on_endpoint_changed(self.endpoint_combo.currentText())

    def _on_endpoint_changed(self, endpoint: str):
        organ = self.organ_combo.currentText()
        self.author_combo.blockSignals(True)
        self.author_combo.clear()
        sets = get_parameter_sets(organ, endpoint, self._entries)
        self.author_combo.addItems([s.label for s in sets])
        self.author_combo.blockSignals(False)
        self._on_author_changed(self.author_combo.currentText())

    def _on_author_changed(self, label: str):
        organ = self.organ_combo.currentText()
        endpoint = self.endpoint_combo.currentText()
        sets = get_parameter_sets(organ, endpoint, self._entries)
        entry = next((s for s in sets if s.label == label), None)
        self._current_entry = entry
        if entry is None:
            self.detail_view.setHtml("")
            return

        status_note = {
            "verified_unique": "Verified -- unique parameter set in the bank for this organ/endpoint.",
            "verified_alternative_overlap": "Verified -- alternative/partial-overlap parameter set; check which fits your case.",
            "verified_distinct_endpoint": "Verified -- distinct endpoint (not a direct replacement for other entries).",
            "verified_table2": "Verified directly against the source's own published table.",
            "unverified_citation_caution": "\u26a0 Citation could not be independently confirmed -- values appear plausible, use with caution.",
            "incomplete_reference_only": "Incomplete -- missing required numeric parameters; reference only.",
            # older-bank status strings, kept for backward compatibility
            "historical": "Historical reference fit.",
            "quantec_update": "QUANTEC-era update / confirmation.",
            "conditional": "Conditional alternative -- check endpoint/cohort match before using.",
            "conditional_protons_only": "Conditional -- PROTON THERAPY cohort only, do not apply to photon plans.",
            "conditional_research_small_cohort": "Conditional -- small research cohort, preliminary evidence.",
            "unreviewed_caution": "Not fully vetted by the evidence review -- use with extra caution.",
        }.get(entry.status, entry.status)

        html = f"""
        <b>{entry.organ} &mdash; {entry.endpoint}</b><br>
        <i>{entry.label}</i><br><br>
        n = {entry.n}, m = {entry.m}, TD50 = {entry.td50_gy} Gy<br>
        Reference volume: {entry.vref}<br>
        Dose reference: {entry.dose_reference}<br>
        Evidence status: {status_note}<br><br>
        <b>Source:</b> {entry.source}<br>
        {"<b>URL:</b> " + entry.url if entry.url else ""}<br><br>
        <b>Notes:</b> {entry.notes}
        """
        self.detail_view.setHtml(html)
        self.name_edit.setText(f"{entry.organ} - {entry.endpoint} ({entry.label})")

        if entry.alpha_beta_missing:
            self.warning_label.setText(
                "\u26a0 This source did NOT report alpha/beta. Enter a value below before "
                "adding this endpoint -- do not guess; use a literature-supported value for "
                "this tissue type and record where it came from."
            )
            self.alpha_beta_edit.clear()
            self.alpha_beta_edit.setEnabled(True)
        else:
            self.warning_label.setText("")
            self.alpha_beta_edit.setText(str(entry.alpha_beta))
            self.alpha_beta_edit.setEnabled(True)  # still editable, but pre-filled

    # ------------------------------------------------------------------ #
    def _on_accept(self):
        entry = self._current_entry
        if entry is None:
            return
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setFocus()
            return
        try:
            alpha_beta = float(self.alpha_beta_edit.text())
        except ValueError:
            QMessageBox.warning(self, "alpha/beta required",
                                 "Enter a numeric alpha/beta value (Gy) before adding this endpoint.")
            self.alpha_beta_edit.setFocus()
            return

        params = LKBParams(td50=entry.td50_gy * 100.0, m=entry.m, n=entry.n, alpha_beta=alpha_beta)
        ntcp_ep = NTCPEndpoint(name=name, model="LKB", alpha_beta=alpha_beta, params=params)
        self.result_endpoint = EndpointDefinition(name=name, kind="NTCP", model="LKB", ntcp_endpoint=ntcp_ep)
        self.accept()
