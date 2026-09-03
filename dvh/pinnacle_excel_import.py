"""
dvh/pinnacle_excel_import.py

Parser for the native Pinnacle "Points[] = {...}" DVH-export block format,
as found when a Pinnacle differential-DVH export is pasted/saved into an
Excel workbook (one such workbook -> one patient -> one sheet per patient
is the layout used by the user's `Book1.xlsx`, matching what the paper
describes: "BioSuite can read absolute differential DVHs directly from
Pinnacle").

Each structure occupies a horizontal block of (at least) 2 columns:

    Row 0:  <Structure name>
    Row 1:  NumberOfDimensions = 2;
    Row 2:  NumberOfPoints = N;
    Row 3:  Points[] ={
    Row 4..(4+N-1):  <dose_cGy>, <volume_cc>   (one differential-DVH bin per row)
    Row 4+N:  };

Multiple structures are laid out side-by-side, each block starting at some
column c (dose) / c+1 (volume), usually followed by one blank spacer
column before the next structure's block. Column offsets are NOT assumed
to be regular -- we detect each block by scanning row 0 for structure-name
cells and row 2/3 for the corresponding metadata, which is robust to the
irregular spacing actually observed (3-column blocks except a 2-column
last block).
"""
from __future__ import annotations
import re
import pandas as pd
import numpy as np

from core.dvh import DVH


_N_POINTS_RE = re.compile(r"NumberOfPoints\s*=\s*(\d+)")


def _is_structure_name_cell(value) -> bool:
    if not isinstance(value, str):
        return False
    v = value.strip()
    if not v:
        return False
    # exclude the metadata keyword rows themselves
    if v.startswith(("NumberOfDimensions", "NumberOfPoints", "Points[]", "};")):
        return False
    return True


def read_pinnacle_sheet(path: str, sheet_name) -> dict[str, DVH]:
    """
    Parse ONE sheet (= one patient) of a Pinnacle-export Excel workbook
    into a dict of structure_name -> differential DVH (dose in cGy, volume
    in cc), auto-detecting each structure's column block.
    """
    df = pd.read_excel(path, sheet_name=sheet_name, header=None)
    n_rows, n_cols = df.shape

    structures: dict[str, DVH] = {}
    c = 0
    while c < n_cols:
        cell0 = df.iat[0, c] if 0 < n_rows else None
        if _is_structure_name_cell(cell0):
            name = str(cell0).strip()
            # locate "NumberOfPoints = N;" -- normally row 2, but scan a
            # small window in case of extra/missing header rows
            n_points = None
            points_header_row = None
            for r in range(1, min(6, n_rows)):
                cell = df.iat[r, c]
                if isinstance(cell, str):
                    m = _N_POINTS_RE.search(cell)
                    if m:
                        n_points = int(m.group(1))
                    if cell.strip().startswith("Points[]"):
                        points_header_row = r
            if n_points is not None and points_header_row is not None:
                data_start = points_header_row + 1
                data_end = data_start + n_points  # exclusive
                if data_end <= n_rows and c + 1 < n_cols:
                    dose = pd.to_numeric(
                        df.iloc[data_start:data_end, c], errors="coerce"
                    ).to_numpy(dtype=float)
                    vol = pd.to_numeric(
                        df.iloc[data_start:data_end, c + 1], errors="coerce"
                    ).to_numpy(dtype=float)
                    valid = ~(np.isnan(dose) | np.isnan(vol))
                    dose, vol = dose[valid], vol[valid]
                    # de-duplicate structure names if repeated across the sheet
                    key = name
                    suffix = 2
                    while key in structures:
                        key = f"{name}_{suffix}"
                        suffix += 1
                    structures[key] = DVH(name, dose, vol)
        c += 1

    return structures


def read_all_patients(path: str) -> dict[str, dict[str, DVH]]:
    """Parse EVERY sheet (= every patient) of the workbook.
    Returns dict: sheet_name -> {structure_name -> DVH}."""
    xls = pd.ExcelFile(path)
    return {sheet: read_pinnacle_sheet(path, sheet) for sheet in xls.sheet_names}
