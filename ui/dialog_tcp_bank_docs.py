"""
ui/dialog_tcp_bank_docs.py
"TCP parameter bank -- methodology & references" dialog, reachable from
the Radiobiology menu. Explains the Target/Poisson TCP evidence bank's
structure, the model-family gating, and -- most importantly -- the
K-vs-density distinction, so users understand exactly what they're
importing and why some fields require their own input.
"""
from __future__ import annotations
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton, QHBoxLayout


class TCPBankDocsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TCP parameter bank \u2014 methodology & references")
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
        <h2>TCP parameter bank &mdash; methodology &amp; references</h2>
        <p style="color:#666;">Evidence version: 31 August 2026 (row-by-row re-verification
        pass against original source papers). Systematic search window 2000-2026, priority
        given to the van Leeuwen et al. 2018 systematic review, then general reviews, then
        primary open-access Poisson-TCP modelling studies.</p>

        <h3>What this bank IS and ISN'T</h3>
        <p>This is a <b>literature/evidence compilation</b>, not a clinical default-parameter
        library. Alpha, alpha/beta, clonogen and repopulation values are model- and
        setting-specific. <b>A blank/missing field means "not reported", never zero</b> --
        BioSuite-NG will always ask you to supply it explicitly rather than guessing.</p>

        <h3>The most important rule in this bank: K vs. density</h3>
        <p><b>"Total clonogens K"</b> (an absolute count for the specific reported cohort)
        and <b>"Clonogen density (per cc)"</b> are <u>NOT interchangeable</u> without the
        source study's own reference volume. When a record only reports K (e.g. Huang et al.
        2012's cervix fit, K=139), the "Add from TCP parameter bank" dialog will ask you for
        YOUR case's GTV volume and divide K by it to obtain a density -- this is a
        <b>re-interpretation</b> of that K against your volume, not a validated general
        density, and is flagged with a visible warning every time.</p>

        <h3>Model-family gating</h3>
        <ul>
          <li><b>poisson_lq_repopulation</b> &mdash; directly matches BioSuite-NG's Marsden
          (LQ-Poisson + accelerated repopulation) engine.</li>
          <li><b>lq_protraction_repair</b> &mdash; the source additionally reports
          sublethal-repair/dose-protraction detail (mu, repair half-time). BioSuite-NG
          currently imports these as a standard Marsden-model endpoint and does NOT yet use
          the repair-specific fields in the bank-import dialog (they remain visible in the
          record's detail panel for reference).</li>
          <li><b>alpha_beta_evidence_only</b> &mdash; the source reports ONLY alpha and
          alpha/beta (most of the van Leeuwen et al. 2018 systematic-review extractions).
          Treat these purely as an alpha/alpha-beta evidence source -- density, spread and
          repopulation must be your own working assumptions, entered explicitly.</li>
          <li><b>zaider_minerbo</b> and other incompatible families &mdash; a genuinely
          different mathematical formalism (e.g. time-dependent re-sensitisation) that
          BioSuite-NG's engine cannot reproduce. Kept in the bank for documentation/
          transparency only; not selectable in the Add dialog.</li>
        </ul>

        <h3>Clinical-use limitation</h3>
        <p>Independent clinical validation and physicist/oncologist review are required
        before any patient-level use. Extreme values from targeted-radionuclide-therapy or
        HDR-brachytherapy models should not be transferred directly to conventional EBRT.</p>

        <h3>Primary references</h3>
        <ul>
          <li>van Leeuwen CM, Oei AL, Crezee J, et al. The alfa and beta of tumours: a review
          of parameters of the linear-quadratic model, derived from clinical radiotherapy
          studies. <i>Radiat Oncol.</i> 2018;13:96.
          <a href="https://doi.org/10.1186/s13014-018-1040-z">doi:10.1186/s13014-018-1040-z</a></li>
          <li>El Sharouni SY, et al. Tumour Control Probability of Stage III Inoperable NSCLC
          after Sequential Chemo-radiotherapy. 2005 (NSCLC Poisson-TCP parameters).</li>
          <li>Wang JZ, Li XA. Impact of prolonged fraction delivery times on tumor control.
          <i>Int J Radiat Oncol Biol Phys.</i> 2003. (Prostate sublethal-repair parameters.)</li>
          <li>Every record's full citation and DOI/link is shown in its own tile in the "Add
          from TCP parameter bank" dialog, and in <code>data/tcp_parameter_bank.json</code>.</li>
        </ul>
        <p style="color:#777; font-size: 11px;">See the User Manual (Help menu) for a
        walk-through of the Add-from-bank dialogs, and the Radiobiology menu's "LKB
        parameter bank" entry for the corresponding NTCP documentation.</p>
        """
