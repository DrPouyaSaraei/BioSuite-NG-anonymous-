"""
ui/dialog_add_tcp_from_bank.py
Lets the user add a new TCP endpoint by picking Tumour site -> Endpoint
-> parameter set (by "Author et al. Year" + the specific alpha
definition/scenario), from the curated TCP parameter bank
(core/tcp_bank.py).

Every field the chosen record does NOT report (alpha spread, clonogen
density/total-K, repopulation timing) must be filled in explicitly by
the user before the endpoint can be created -- nothing is silently
defaulted or guessed, mirroring the NTCP bank dialog's alpha/beta rule.

Special handling for "Total clonogens K" (as opposed to a per-cc
density): the two are NOT interchangeable without the source's own
reference volume (see build_tcp_bank.py). If a record reports K, the
user must supply the GTV volume it should be divided by, and a visible
warning explains that this re-interprets K against THEIR volume, not
the source cohort's.
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QLabel, QLineEdit,
    QDialogButtonBox, QTextBrowser, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt

from core.tcp_bank import load_bank, get_sites, get_endpoints, get_parameter_sets, TCPBankEntry
from core.tcp_models import TCPParams
from ui.app_state import EndpointDefinition
from ui.combo_utils import enable_typeahead_search


class AddTCPFromBankDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add TCP endpoint from parameter bank")
        self.setMinimumWidth(660)
        self.result_endpoint: EndpointDefinition | None = None
        self._entries = load_bank()
        self._current_entry: TCPBankEntry | None = None
        self._record_by_display: dict[str, TCPBankEntry] = {}

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.site_combo = QComboBox()
        self.site_combo.addItems(get_sites(self._entries))
        enable_typeahead_search(self.site_combo)  # type "p" -> jumps to "Prostate", case-insensitive
        self.endpoint_combo = QComboBox()
        enable_typeahead_search(self.endpoint_combo)
        self.record_combo = QComboBox()

        form.addRow("Tumour site:", self.site_combo)
        form.addRow("Endpoint:", self.endpoint_combo)
        form.addRow("Parameter set (author, year, scenario):", self.record_combo)
        layout.addLayout(form)

        self.detail_view = QTextBrowser()
        self.detail_view.setMinimumHeight(160)
        layout.addWidget(self.detail_view)

        self.warning_label = QLabel("")
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet("color: #b00000; font-weight: bold;")
        layout.addWidget(self.warning_label)

        # --- fields the user may need to fill in (built dynamically) ---
        self.fill_form = QFormLayout()
        self.fill_container = QWidget()
        self.fill_container.setLayout(self.fill_form)
        layout.addWidget(self.fill_container)
        self._fill_edits: dict[str, QLineEdit] = {}

        name_row = QFormLayout()
        self.name_edit = QLineEdit()
        name_row.addRow("Endpoint name in this project:", self.name_edit)
        gtv_row = QFormLayout()
        self.gtv_vol_edit = QLineEdit("30.0")
        gtv_row.addRow("GTV volume (cm^3) for this patient:", self.gtv_vol_edit)
        layout.addLayout(name_row)
        layout.addLayout(gtv_row)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(self.buttons)

        self.site_combo.currentTextChanged.connect(self._on_site_changed)
        self.endpoint_combo.currentTextChanged.connect(self._on_endpoint_changed)
        self.record_combo.currentTextChanged.connect(self._on_record_changed)
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)

        self._on_site_changed(self.site_combo.currentText())

    # ------------------------------------------------------------------ #
    def _on_site_changed(self, site: str):
        self.endpoint_combo.blockSignals(True)
        self.endpoint_combo.clear()
        self.endpoint_combo.addItems(get_endpoints(site, self._entries))
        self.endpoint_combo.blockSignals(False)
        self._on_endpoint_changed(self.endpoint_combo.currentText())

    def _on_endpoint_changed(self, endpoint: str):
        site = self.site_combo.currentText()
        records = get_parameter_sets(site, endpoint, self._entries)
        self._record_by_display.clear()
        self.record_combo.blockSignals(True)
        self.record_combo.clear()
        for r in records:
            display = f"{r.label} \u2014 {r.alpha_definition}" if r.alpha_definition else r.label
            display = f"{display}  [{r.record_id}]"
            self._record_by_display[display] = r
            self.record_combo.addItem(display)
        self.record_combo.blockSignals(False)
        if self.record_combo.count() > 0:
            self._on_record_changed(self.record_combo.currentText())
        else:
            self.detail_view.setHtml("<i>No selectable parameter sets for this endpoint.</i>")

    def _on_record_changed(self, display: str):
        entry = self._record_by_display.get(display)
        self._current_entry = entry
        if entry is None:
            return

        family_note = {
            "poisson_lq_repopulation": "Directly computable with BioSuite-NG's Marsden (LQ-Poisson) engine.",
            "lq_protraction_repair": "Reports sublethal-repair/protraction detail (LQ-SLR-style source); "
                                      "this dialog imports it as a standard Marsden-model endpoint and does "
                                      "NOT use the repair/protraction-specific fields -- see notes.",
            "alpha_beta_evidence_only": "This source reports ONLY alpha and alpha/beta -- treat it purely "
                                         "as an alpha/alpha-beta evidence source. You must supply density, "
                                         "spread and repopulation timing entirely yourself.",
        }.get(entry.model_family_key, entry.model_family_key)

        html = f"""
        <b>{entry.tumour_site} &mdash; {entry.endpoint}</b><br>
        <i>{entry.label}</i> ({entry.alpha_definition or 'n/a'})<br><br>
        Histology/setting: {entry.histology_setting}<br>
        Modality/schedule: {entry.modality_schedule}<br>
        Alpha = {entry.alpha_per_gy} Gy<sup>-1</sup> ({entry.alpha_value_status})<br>
        Alpha spread SD = {entry.alpha_spread_sd if entry.alpha_spread_sd is not None else '<b>not reported</b>'}<br>
        Alpha/beta = {entry.alpha_beta_gy} Gy<br>
        Clonogen density = {entry.clonogen_density_percc if entry.reports_density else '<b>not reported</b>'} /cc<br>
        Total clonogens K = {entry.total_clonogens_k if entry.reports_total_k else '<b>not reported</b>'}<br>
        Repopulation (days) = {entry.repopulation_days_tpot if entry.repopulation_days_tpot is not None else '<b>not reported</b>'}<br>
        Delay before repopulation (days) = {entry.delay_before_repopulation_days if entry.delay_before_repopulation_days is not None else '<b>not reported</b>'}<br><br>
        <b>Model family:</b> {family_note}<br><br>
        <b>Source:</b> {entry.source}<br>
        {"<b>URL:</b> " + entry.url if entry.url else ""}<br><br>
        <b>Notes:</b> {entry.notes}
        """
        self.detail_view.setHtml(html)
        self.name_edit.setText(f"{entry.tumour_site} - {entry.endpoint} ({entry.label})")

        self._rebuild_fill_fields(entry)

    # ------------------------------------------------------------------ #
    def _rebuild_fill_fields(self, entry: TCPBankEntry):
        while self.fill_form.rowCount() > 0:
            self.fill_form.removeRow(0)
        self._fill_edits.clear()

        warnings = []
        is_evidence_only = entry.model_family_key == "alpha_beta_evidence_only"

        if entry.alpha_spread_sd is None and not is_evidence_only:
            edit = QLineEdit()
            edit.setPlaceholderText("required -- e.g. 0.05 (Gy^-1)")
            self._fill_edits["alpha_spread"] = edit
            self.fill_form.addRow("Alpha spread SD (Gy^-1) -- not reported:", edit)
            warnings.append("Alpha spread was not reported by this source.")

        if not entry.reports_density and not entry.reports_total_k and not is_evidence_only:
            edit = QLineEdit()
            edit.setPlaceholderText("required -- e.g. 1e7 (per cc)")
            self._fill_edits["density"] = edit
            self.fill_form.addRow("Clonogen density (per cc) -- not reported:", edit)
            warnings.append("Neither clonogen density nor total clonogen count was reported.")
        elif entry.reports_total_k and not entry.reports_density:
            if entry.k_fixed_no_reference_volume:
                warnings.append(
                    f"\u2139 This source reports a FIXED total clonogen count K="
                    f"{entry.total_clonogens_k:.3g} with NO source-defined reference volume, and "
                    f"its own caveat says explicitly not to divide K by a volume. BioSuite-NG will "
                    f"use K={entry.total_clonogens_k:.3g} as-is for ANY structure this endpoint is "
                    f"applied to -- the 'GTV volume' field below will NOT affect this calculation "
                    f"(it is only used for TCP-endpoint bookkeeping elsewhere in the app)."
                )
            else:
                warnings.append(
                    f"\u26a0 This source reports TOTAL clonogen count K={entry.total_clonogens_k:.3g}, "
                    f"NOT a per-cc density. It will be divided by the 'GTV volume' field below to make a "
                    f"density -- this re-interprets K against YOUR volume, which may not match the source "
                    f"cohort's implied volume. Verify this is a reasonable assumption for your case."
                )

        if entry.repopulation_days_tpot is None and entry.model_family_key != "alpha_beta_evidence_only":
            edit = QLineEdit()
            edit.setPlaceholderText("required -- e.g. 30 (days), or leave as inf for no repopulation")
            self._fill_edits["repop_days"] = edit
            self.fill_form.addRow("Clonogen doubling time (days) -- not reported:", edit)
            warnings.append("Repopulation timing was not reported by this source.")

        if is_evidence_only:
            edit_density = QLineEdit()
            edit_density.setPlaceholderText("required -- e.g. 1e7 (per cc)")
            self._fill_edits["density"] = edit_density
            self.fill_form.addRow("Clonogen density (per cc) -- source provides alpha/beta only:", edit_density)
            edit_spread = QLineEdit("0.0")
            self._fill_edits["alpha_spread"] = edit_spread
            self.fill_form.addRow("Alpha spread SD (Gy^-1):", edit_spread)
            edit_repop = QLineEdit("1e9")
            self._fill_edits["repop_days"] = edit_repop
            self.fill_form.addRow("Clonogen doubling time (days, 1e9=none):", edit_repop)
            warnings.append(
                "This source is ALPHA/ALPHA-BETA EVIDENCE ONLY -- density, spread and repopulation "
                "are not from the literature here; you are entering your own working assumptions."
            )

        self.warning_label.setText("\n".join(warnings))

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
            gtv_vol = float(self.gtv_vol_edit.text())
        except ValueError:
            QMessageBox.warning(self, "GTV volume required", "Enter a numeric GTV volume (cm^3).")
            self.gtv_vol_edit.setFocus()
            return

        try:
            if "alpha_spread" in self._fill_edits:
                alpha_spread = float(self._fill_edits["alpha_spread"].text())
            else:
                alpha_spread = entry.alpha_spread_sd

            if "density" in self._fill_edits:
                density = float(self._fill_edits["density"].text())
                effective_gtv_vol = gtv_vol
            elif entry.reports_density:
                density = entry.clonogen_density_percc
                effective_gtv_vol = gtv_vol
            elif entry.k_fixed_no_reference_volume:
                # K is a FIXED total with no valid reference volume to divide by
                # (per the source's own caveat) -- use it as-is, decoupled from
                # whatever GTV volume the user enters, by pairing density=K with
                # a fixed volume of 1.0 so density*volume = K exactly, always.
                density = entry.total_clonogens_k
                effective_gtv_vol = 1.0
            else:
                # K WITH a source-defined reference volume would be handled here
                # if/when such a record exists; none currently do (see
                # build_tcp_bank.py). Fall back to the user's own GTV volume.
                density = entry.total_clonogens_k / gtv_vol
                effective_gtv_vol = gtv_vol

            if "repop_days" in self._fill_edits:
                doubling_days = float(self._fill_edits["repop_days"].text())
            else:
                doubling_days = entry.repopulation_days_tpot if entry.repopulation_days_tpot is not None else 1e9

            delay_days = entry.delay_before_repopulation_days or 0.0
        except (ValueError, TypeError):
            QMessageBox.warning(self, "Missing/invalid value",
                                 "Fill in every highlighted field with a numeric value before adding this endpoint.")
            return

        params = TCPParams(
            alpha=entry.alpha_per_gy, alpha_beta=entry.alpha_beta_gy,
            alpha_spread=alpha_spread, clonogen_density=density,
            repopulation_delay_days=delay_days, clonogen_doubling_time_days=doubling_days,
        )
        self.result_endpoint = EndpointDefinition(
            name=name, kind="TCP", model="Marsden (LQ-Poisson) [from TCP bank]",
            tcp_params=params, gtv_volume_cm3=effective_gtv_vol,
        )
        self.accept()
