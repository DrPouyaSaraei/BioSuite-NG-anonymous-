"""
ui/dialog_lkb_bank_docs.py
"LKB parameter bank -- methodology & references" dialog, reachable from
the Radiobiology menu (next to Help). Translates and summarises the
methodology/usage-guide and references sheets from the bundled evidence
workbook (data/Radiobiological_TCP_NTCP.xlsx), so users can trust where
every parameter set in the bank comes from.
"""
from __future__ import annotations
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton, QHBoxLayout


class LKBBankDocsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LKB parameter bank \u2014 methodology & references")
        self.resize(760, 640)

        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(self._html())
        layout.addWidget(browser)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    @staticmethod
    def _html() -> str:
        return """
        <h2>LKB parameter bank &mdash; methodology &amp; references</h2>
        <p style="color:#666;">Evidence version: 31 August 2026 (row-by-row re-verification
        pass against original source papers; ~35 of 44 distinct sources independently
        re-checked against PubMed/journal primary literature). Historical values from the
        original bank were never overwritten; new evidence was added as separate,
        citable, endpoint/modality-specific entries instead.</p>

        <h3>How to read a parameter set</h3>
        <ul>
          <li>The LKB model itself has exactly <b>three</b> intrinsic parameters:
          <b>TD50</b>, <b>m</b>, and <b>n</b>. <b>alpha/beta is NOT an intrinsic LKB
          parameter</b> &mdash; it is only used to convert dose between different
          fractionation schedules (EQD2 correction).</li>
          <li>When a source did not report alpha/beta, the bank marks it as
          <i>not reported</i>. BioSuite-NG will ask you to supply a value explicitly
          before that parameter set can be used for EQD2 conversion &mdash; a value is
          never invented silently.</li>
          <li><b>TD50 is only valid in the dose reference the source paper actually
          used</b>: physical dose, EQD2, EQD25, or Gy(RBE) are NOT interchangeable.
          Check each entry's "Dose reference" field before combining it with your own
          DVH.</li>
        </ul>

        <h3>Evidence status labels used in the bank</h3>
        <ul>
          <li><b>verified_unique</b> &mdash; a verified, unique parameter set in the
          bank for this organ/endpoint combination.</li>
          <li><b>verified_alternative_overlap</b> &mdash; verified, but an
          alternative/partial-overlap set exists for the same organ; check which one
          actually matches your endpoint, cohort and dose reference before using it.</li>
          <li><b>verified_distinct_endpoint</b> &mdash; verified, and reports a
          genuinely distinct endpoint &mdash; not a direct replacement for any other
          entry in the bank.</li>
          <li><b>verified_table2</b> &mdash; verified directly against the source
          paper's own published table.</li>
          <li><b>unverified_citation_caution</b> &mdash; the numeric values look
          plausible, but the citation itself could not be independently located in
          PubMed/ScienceDirect/Google Scholar during the audit; use with extra
          scrutiny (see that entry's Notes field for detail).</li>
          <li><b>incomplete_reference_only</b> &mdash; missing one of n / m / TD50;
          kept for transparency but <b>not selectable</b> in the "Add from LKB
          parameter bank" dialog.</li>
        </ul>

        <h3>An update replaces the historical value ONLY if...</h3>
        <p>...the structure, endpoint, toxicity grade, scoring method, treatment
        modality, dose/fractionation, and DVH-reduction method are all consistent with
        the historical entry. In most cases in this bank, new evidence is kept as an
        <i>alternative/overlapping option</i> or a <i>new endpoint</i> alongside the
        historical value &mdash; not a wholesale replacement of Burman/QUANTEC.</p>

        <h3>Validation caveat</h3>
        <p>A 2023 systematic review (Dennst&auml;dt et al.) found 509 different LKB
        parameter sets across 130 papers, with very large heterogeneity in the
        resulting NTCP predictions. <b>Every parameter set should be locally validated
        against your own cohort, or at minimum an independent cohort, before it
        informs a clinical decision.</b> This bank is an evidence map and documented
        parameter source, not a substitute for institutional protocols, dose
        constraints, or the judgement of the treating radiation oncologist/physicist.</p>

        <h3>Primary references</h3>
        <ul>
          <li>Burman C, Kutcher GJ, Emami B, Goitein M. Fitting of normal tissue
          tolerance data to an analytic function. <i>Int J Radiat Oncol Biol Phys.</i>
          1991;21:123&ndash;135.
          <a href="https://doi.org/10.1016/0360-3016(91)90172-Z">doi:10.1016/0360-3016(91)90172-Z</a></li>
          <li>Dennst&auml;dt F, Medov&aacute; M, Putora PM, Glatzer M. Parameters of the
          Lyman Model for Calculation of Normal-Tissue Complication Probability: A
          Systematic Literature Review. <i>Int J Radiat Oncol Biol Phys.</i>
          2023;115:696&ndash;706.
          <a href="https://doi.org/10.1016/j.ijrobp.2022.08.039">doi:10.1016/j.ijrobp.2022.08.039</a></li>
          <li>Individual QUANTEC organ reviews (<i>Int J Radiat Oncol Biol Phys.</i>
          2010;76(3 Suppl)) &mdash; Michalski et al. (rectum), Marks et al. (lung),
          Pan et al. (liver), Dawson et al. (kidney).</li>
          <li>Every entry's full citation is shown in its own tile in the "Add from
          LKB parameter bank" dialog, and in <code>data/lkb_parameter_bank.json</code>.</li>
        </ul>
        <p style="color:#777; font-size: 11px;">See the User Manual (Help menu) for a
        walk-through of how to add and use a bank entry.</p>
        """
