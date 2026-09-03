"""
ui/main_window.py
Main application window for BioSuite-NG: reproduces the original BioSuite
window chrome (File/Radiobiology/Help menu, "Current treatment plan:"
label, tabbed panel), with the AJUMS Medical Physics Research Group logo
as the window/app icon, and tabs ordered per user request (Model/Endpoint
parameters comes BEFORE DVH import, since endpoints must exist before a
DVH can usefully be associated to one).
"""
from __future__ import annotations
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QTabWidget, QMessageBox
)
from PyQt6.QtGui import QAction, QIcon

from ui.app_state import AppState
from ui.tab_treatment_plans import TreatmentPlansTab
from ui.tab_dvh_import import DVHImportTab
from ui.tab_model_params import ModelEndpointTab
from ui.tab_dvh_plots import DVHPlotsTab
from ui.tab_drc import DRCTab
from ui.tab_optimisation import OptimisationTab
from ui.tab_fitting import FittingTab
from ui.dialog_about import AboutDialog
from ui.dialog_lkb_bank_docs import LKBBankDocsDialog
from ui.dialog_tcp_bank_docs import TCPBankDocsDialog
from ui.dialog_export import ExportDialog
from core.paths import resource_path

ASSETS_DIR = resource_path("assets")
ICON_PATH = os.path.join(ASSETS_DIR, "biosuite_ng.ico")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BioSuite-NG")
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        self.resize(1150, 800)

        self.state = AppState()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        header = QLabel("Current treatment plan :")
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(TreatmentPlansTab(self.state), "Treatment plans")
        self.tabs.addTab(ModelEndpointTab(self.state), "Model/Endpoint parameters")
        self.tabs.addTab(DVHImportTab(self.state), "DVH import")
        self.tabs.addTab(DVHPlotsTab(self.state), "DVH plots")
        self.tabs.addTab(DRCTab(self.state), "Dose response curves")
        self.tabs.addTab(OptimisationTab(self.state), "Optimisation")
        self.tabs.addTab(FittingTab(self.state), "Fitting")
        layout.addWidget(self.tabs)

        self._build_menu()

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        radiobiology_menu = menubar.addMenu("&Radiobiology")
        about_models_action = QAction("About the models...", self)
        about_models_action.triggered.connect(self._show_about_models)
        radiobiology_menu.addAction(about_models_action)

        lkb_bank_action = QAction("LKB parameter bank (methodology && references)...", self)
        lkb_bank_action.triggered.connect(self._show_lkb_bank_docs)
        radiobiology_menu.addAction(lkb_bank_action)

        tcp_bank_action = QAction("TCP parameter bank (methodology && references)...", self)
        tcp_bank_action.triggered.connect(self._show_tcp_bank_docs)
        radiobiology_menu.addAction(tcp_bank_action)

        radiobiology_menu.addSeparator()
        export_action = QAction("Export...", self)
        export_action.triggered.connect(self._show_export)
        radiobiology_menu.addAction(export_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction("About BioSuite-NG", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        manual_action = QAction("User manual (PDF)...", self)
        manual_action.triggered.connect(self._open_manual)
        help_menu.addAction(manual_action)

    def _show_about(self):
        dlg = AboutDialog(self)
        dlg.exec()

    def _open_manual(self):
        manual_path = resource_path("docs", "BioSuite-NG_User_Manual.pdf")
        if os.path.exists(manual_path):
            import subprocess
            import sys as _sys
            try:
                if _sys.platform.startswith("win"):
                    os.startfile(manual_path)  # type: ignore[attr-defined]
                elif _sys.platform == "darwin":
                    subprocess.Popen(["open", manual_path])
                else:
                    subprocess.Popen(["xdg-open", manual_path])
            except Exception:
                QMessageBox.information(self, "User manual",
                                         f"Manual is at:\n{manual_path}")
        else:
            QMessageBox.information(
                self, "User manual",
                "docs/BioSuite-NG_User_Manual.pdf not found alongside the app."
            )

    def _show_about_models(self):
        QMessageBox.information(
            self, "Radiobiological models",
            "TCP: LQ-Poisson 'Marsden' (+ accelerated repopulation), LQ-SLR\n"
            "NTCP: LKB, Relative Seriality, Simple Maximum Dose, EUD (Niemierko)\n\n"
            "See README.md for full references."
        )

    def _show_lkb_bank_docs(self):
        dlg = LKBBankDocsDialog(self)
        dlg.exec()

    def _show_tcp_bank_docs(self):
        dlg = TCPBankDocsDialog(self)
        dlg.exec()

    def _show_export(self):
        dlg = ExportDialog(self.state, self)
        dlg.exec()
