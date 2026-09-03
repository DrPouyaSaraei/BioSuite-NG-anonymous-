"""
ui/dialog_about.py
Professional "About" dialog for BioSuite-NG: logo, developer credit,
affiliation, citation to the original Uzan & Nahum paper, list of new
features, and the DISCLAIMER block (matching the wording style used in
the original BioSuite's About screen, adapted for BioSuite-NG).
"""
from __future__ import annotations
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QTextBrowser, QHBoxLayout
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from core.paths import resource_path

ASSETS_DIR = resource_path("assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo_square.png")


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About BioSuite-NG")
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)

        top_row = QHBoxLayout()
        if os.path.exists(LOGO_PATH):
            logo_label = QLabel()
            pix = QPixmap(LOGO_PATH).scaledToWidth(110, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pix)
            top_row.addWidget(logo_label)

        title_col = QVBoxLayout()
        name_label = QLabel("BioSuite-NG")
        name_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        subtitle_label = QLabel("Radiobiological treatment-optimisation software")
        subtitle_label.setStyleSheet("color: #555;")
        title_col.addWidget(name_label)
        title_col.addWidget(subtitle_label)
        title_col.addStretch()
        top_row.addLayout(title_col)
        top_row.addStretch()
        layout.addLayout(top_row)

        body = QTextBrowser()
        body.setOpenExternalLinks(True)
        body.setHtml(self._html())
        body.setMinimumHeight(420)
        layout.addWidget(body)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    @staticmethod
    def _html() -> str:
        return """
        <p><b>Developed by:</b> Dr. Pouya Saraei (Saraei P.)<br>
        <b>Affiliation:</b> Department of Medical Physics, Ahvaz Jundishapur
        University of Medical Sciences, Iran.</p>

        <p><b>Based on the radiobiological methodology and model equations
        originally described in:</b><br>
        Uzan J, Nahum AE. Radiobiologically guided optimisation of the
        prescription dose and fractionation scheme in radiotherapy using
        BioSuite. <i>Br J Radiol.</i> 2012;85(1017):1279&ndash;1286.
        doi:10.1259/bjr/20476567</p>

        <p><b>New in BioSuite-NG (not present in the original BioSuite):</b></p>
        <ul>
          <li>EUD/Niemierko NTCP model</li>
          <li>Monte-Carlo confidence intervals on NTCP/TCP (LKB, RS, SMD, EUD)</li>
          <li>Sensitivity (tornado) analysis</li>
          <li>DVH-level 4D dose accumulation</li>
          <li>DICOM-RT import</li>
          <li>Excel / native Pinnacle DVH-block import</li>
          <li>Curated, multi-source LKB parameter bank (88 parameter sets, 51
          organs) &mdash; Radiobiology menu \u2192 "LKB parameter bank"</li>
          <li>Curated Target/Poisson TCP parameter bank (14 parameter sets, 9
          tumour sites) &mdash; Radiobiology menu \u2192 "TCP parameter bank"</li>
          <li>Searchable-as-you-type dropdowns in both parameter banks</li>
          <li>Export of DVH data, NTCP/TCP summaries, and endpoint lists &mdash;
          Radiobiology menu \u2192 "Export..."</li>
        </ul>

        <hr>
        <p style="color:#b00000;"><b>DISCLAIMER</b></p>
        <p><b>IMPORTANT NOTES FOR USERS OF BIOSUITE-NG</b></p>
        <ul>
          <li>Neither the developer nor Ahvaz Jundishapur University of
          Medical Sciences (AJUMS) can be held responsible for any issue
          that may arise from using this software for the treatment of
          patients.</li>
          <li>This program is not destined for clinical use.</li>
          <li>The final clinical decision should always lie with the
          clinician in charge of the case.</li>
        </ul>

        <p style="color:#777; font-size: 11px;">See README.md for full
        documentation, references, and a complete change list.</p>
        """
