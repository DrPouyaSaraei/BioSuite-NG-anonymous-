"""
dvh/excel_import.py

Import DVHs from an Excel workbook. Supports two layouts, auto-detected:

  LAYOUT A ("wide"): one sheet per patient/plan, columns =
      Dose_cGy | Structure1_Volume_cm3 | Structure2_Volume_cm3 | ...
    (first column is the shared dose axis; every other column is one
    structure's differential OR cumulative volume at that dose)

  LAYOUT B ("long"): one sheet, columns =
      Patient | Structure | Dose_cGy | Volume_cm3
    (one row per dose bin; multiple structures/patients stacked)

Both cumulative and differential DVHs are accepted (auto-detected: if
volume is non-increasing with dose, it's treated as cumulative and
differentiated).

This module is deliberately liberal about column-naming (case-insensitive,
tolerates 'Dose (Gy)' vs 'Dose_cGy' etc.) since real-world export sheets
vary a lot between centres/TPS.
"""
from __future__ import annotations
import re
import numpy as np
import pandas as pd
from typing import Optional

from core.dvh import DVH


def _find_dose_unit_and_scale(col_name: str) -> float:
    """Return the multiplier to convert this column's dose values to cGy."""
    name = col_name.lower()
    if "cgy" in name:
        return 1.0
    if "gy" in name:  # 'Gy' but not 'cGy' (already checked above)
        return 100.0
    # no explicit unit -> assume cGy if values look large, else caller decides
    return 1.0


def _cumulative_to_differential(dose: np.ndarray, cum_vol: np.ndarray) -> np.ndarray:
    """Convert a cumulative DVH (volume >= dose) to differential (volume in each bin)."""
    order = np.argsort(dose)
    d = dose[order]
    v = cum_vol[order]
    diff = -np.diff(v, append=v[-1] - (v[-1] - v[-2] if len(v) > 1 else 0))
    diff = np.append(-np.diff(v), v[-1])
    diff = np.clip(diff, 0, None)
    # restore original order
    out = np.empty_like(diff)
    out[order] = diff
    return out


def _looks_cumulative(volume: np.ndarray) -> bool:
    """Heuristic: cumulative DVHs are (near) monotonically non-increasing with dose."""
    v = np.asarray(volume, dtype=float)
    if len(v) < 3:
        return False
    diffs = np.diff(v)
    return np.mean(diffs <= 1e-9) > 0.8  # >80% of steps non-increasing


def read_dvhs_from_excel(path: str, sheet_name: Optional[str] = None,
                          dose_unit_hint: str = "auto") -> dict[str, DVH]:
    """
    Read all structures' DVHs from one sheet of an Excel workbook.

    Returns dict: structure_name -> DVH (differential, dose in cGy).

    If `sheet_name` is None, uses the first sheet. Call `list_sheets()`
    first if the workbook has one sheet per patient.
    """
    df = pd.read_excel(path, sheet_name=sheet_name or 0)
    df.columns = [str(c).strip() for c in df.columns]

    # ---- detect layout ----
    lower_cols = [c.lower() for c in df.columns]
    is_long = {"patient", "structure", "dose", "volume"}.issubset(
        {re.sub(r"[_\s]|\(.*?\)", "", c) for c in lower_cols}
    ) or ("structure" in lower_cols and "dose" in " ".join(lower_cols))

    result: dict[str, DVH] = {}

    if is_long and "structure" in lower_cols:
        # LAYOUT B: long format
        col_map = {c.lower(): c for c in df.columns}
        dose_col = next(c for c in df.columns if "dose" in c.lower())
        vol_col = next(c for c in df.columns if "volume" in c.lower())
        struct_col = next(c for c in df.columns if "structur" in c.lower())

        scale = _find_dose_unit_and_scale(dose_col) if dose_unit_hint == "auto" else \
            (100.0 if dose_unit_hint.lower() == "gy" else 1.0)

        for struct, grp in df.groupby(struct_col):
            dose = grp[dose_col].to_numpy(dtype=float) * scale
            vol = grp[vol_col].to_numpy(dtype=float)
            if _looks_cumulative(vol):
                vol = _cumulative_to_differential(dose, vol)
            result[str(struct)] = DVH(str(struct), dose, vol)

    else:
        # LAYOUT A: wide format, first column = dose
        dose_col = df.columns[0]
        scale = _find_dose_unit_and_scale(dose_col) if dose_unit_hint == "auto" else \
            (100.0 if dose_unit_hint.lower() == "gy" else 1.0)
        dose = df[dose_col].to_numpy(dtype=float) * scale

        for col in df.columns[1:]:
            vol = df[col].to_numpy(dtype=float)
            if np.all(np.isnan(vol)):
                continue
            vol = np.nan_to_num(vol, nan=0.0)
            if _looks_cumulative(vol):
                vol = _cumulative_to_differential(dose, vol)
            struct_name = re.sub(r"[_]?volume[_]?\(?cm3?\)?", "", col, flags=re.IGNORECASE).strip("_ ")
            result[struct_name or col] = DVH(struct_name or col, dose, vol)

    return result


def list_sheets(path: str) -> list[str]:
    """List all sheet names in an Excel workbook (e.g. one per patient)."""
    xls = pd.ExcelFile(path)
    return xls.sheet_names
