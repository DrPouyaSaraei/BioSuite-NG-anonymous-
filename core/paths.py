"""
core/paths.py
Resolves paths to bundled resource files (data/, assets/, docs/) correctly
in EVERY run mode:
  - running from source (`python main.py`)
  - a PyInstaller --onefile exe (resources unpacked to sys._MEIPASS at
    runtime -- this is the ROOT CAUSE of a real bug found in testing:
    build_exe.bat only bundled 'assets', never 'data', so the LKB
    parameter bank JSON was missing inside the packaged .exe and the
    app crashed silently on click, since --windowed hides the traceback)
  - a PyInstaller --onedir exe (resources sit next to the .exe)

Always import paths via this module instead of hand-rolling
os.path.dirname(__file__) chains, so every run mode works consistently.
"""
from __future__ import annotations
import sys
import os


def project_root() -> str:
    """Root folder containing data/, assets/, docs/ -- adapts automatically
    to source vs. frozen (PyInstaller) execution."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(*parts: str) -> str:
    """Absolute path to a bundled resource, e.g. resource_path('data', 'lkb_parameter_bank.json')."""
    return os.path.join(project_root(), *parts)
