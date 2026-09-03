"""
main.py
Entry point for BioSuite-NG.

Startup feedback -- two layers:
  1) PyInstaller NATIVE splash (only active in a --splash build, see
     build_exe.bat): this is shown by the bootloader itself, BEFORE
     Python even starts running -- it's the fastest possible feedback
     for a --onefile .exe, covering the unpack-to-temp-folder step that
     previously showed nothing at all. `import pyi_splash` below is the
     very first thing this file does specifically so nothing delays it.
  2) A Qt QSplashScreen (below, inside main()) as a fallback for
     `python main.py` / non--splash builds, shown right after
     QApplication exists but BEFORE the slow PyQt6/matplotlib/scipy/
     pandas imports happen.
  If startup speed matters more than a single-file exe, build with
  build_exe_fast_start.bat (--onedir) instead -- it has no unpack step
  at all and is the fastest-starting option of the three.

Global exception handling: a real bug was found where clicking "Add from
LKB parameter bank" silently crashed the packaged .exe -- the root cause
was build_exe.bat not bundling the data/ folder, so loading the parameter
bank raised FileNotFoundError inside a Qt slot. Since the app runs
--windowed (no console), that exception had nowhere to be shown and
PyQt6 simply terminated the process. Two fixes are in place now:
  1) build_exe.bat / build_exe_fast_start.bat now bundle data/ too.
  2) A global exception hook (below) catches ANY future unhandled error
     and shows it in a dialog instead of silently closing the app.
"""
try:
    import pyi_splash  # only importable inside a PyInstaller --splash build;
    pyi_splash_available = True
except ImportError:
    pyi_splash = None
    pyi_splash_available = False

import sys
import os
import traceback

from PyQt6.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt

from core.paths import resource_path

ICON_PATH = resource_path("assets", "biosuite_ng.ico")
LOGO_PATH = resource_path("assets", "logo_square.png")


def install_global_exception_hook(app: QApplication):
    """Show unhandled exceptions in a dialog instead of silently crashing
    (critical for a --windowed build, which has no console to show
    tracebacks otherwise)."""
    def handle_exception(exc_type, exc_value, exc_tb):
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        sys.stderr.write(tb_text)
        try:
            box = QMessageBox()
            box.setIcon(QMessageBox.Icon.Critical)
            box.setWindowTitle("BioSuite-NG -- unexpected error")
            box.setText(
                "Something went wrong and the action could not be completed.\n"
                "BioSuite-NG will try to stay open. Details below can help "
                "diagnose the problem (feel free to report them)."
            )
            box.setDetailedText(tb_text)
            box.exec()
        except Exception:
            pass  # if even the error dialog fails, at least stderr has the traceback

    sys.excepthook = handle_exception


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    install_global_exception_hook(app)

    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    splash = None
    if os.path.exists(LOGO_PATH):
        pix = QPixmap(LOGO_PATH).scaledToWidth(220, Qt.TransformationMode.SmoothTransformation)
        splash = QSplashScreen(pix)
        splash.showMessage(
            "Starting BioSuite-NG...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            Qt.GlobalColor.black,
        )
        splash.show()
        app.processEvents()

    # Heavy imports happen HERE, after the splash is already on screen.
    from ui.main_window import MainWindow

    win = MainWindow()
    if os.path.exists(ICON_PATH):
        win.setWindowIcon(QIcon(ICON_PATH))

    win.show()
    if splash is not None:
        splash.finish(win)
    if pyi_splash_available:
        # hand off smoothly from PyInstaller's native (pre-Python) splash
        # to the real window now that it's fully constructed and visible
        pyi_splash.close()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
