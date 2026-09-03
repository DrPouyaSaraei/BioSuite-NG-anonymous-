"""
core/dvh.py
Dose-Volume Histogram data structure, import (DICOM-RT / CSV / Pinnacle-style text)
and EQD2 conversion utilities.

Based on the methodology described in:
Uzan J, Nahum AE. "Radiobiologically guided optimisation of the prescription
dose and fractionation scheme in radiotherapy using BioSuite."
Br J Radiol. 2012;85:1279-1286.
"""

from __future__ import annotations
import csv
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DVH:
    """
    Differential dose-volume histogram.

    dose_bins_cgy : bin-centre doses in cGy (absolute, physical dose as delivered
                    for the number of fractions this DVH was computed for)
    volume_cm3    : absolute volume (cm^3) in each dose bin (differential DVH)
    structure_name: name of the organ / target
    """
    structure_name: str
    dose_bins_cgy: np.ndarray
    volume_cm3: np.ndarray

    def __post_init__(self):
        self.dose_bins_cgy = np.asarray(self.dose_bins_cgy, dtype=float)
        self.volume_cm3 = np.asarray(self.volume_cm3, dtype=float)
        if self.dose_bins_cgy.shape != self.volume_cm3.shape:
            raise ValueError("dose_bins_cgy and volume_cm3 must have the same shape")

    # ------------------------------------------------------------------ #
    # basic derived quantities
    # ------------------------------------------------------------------ #
    @property
    def total_volume_cm3(self) -> float:
        return float(np.sum(self.volume_cm3))

    @property
    def max_dose_cgy(self) -> float:
        nz = self.volume_cm3 > 0
        return float(np.max(self.dose_bins_cgy[nz])) if nz.any() else 0.0

    @property
    def mean_dose_cgy(self) -> float:
        tv = self.total_volume_cm3
        if tv <= 0:
            return 0.0
        return float(np.sum(self.dose_bins_cgy * self.volume_cm3) / tv)

    def cumulative(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (dose, volume_percent) cumulative DVH, descending-dose convention."""
        order = np.argsort(self.dose_bins_cgy)
        d_sorted = self.dose_bins_cgy[order]
        v_sorted = self.volume_cm3[order]
        cum = np.cumsum(v_sorted[::-1])[::-1]  # volume receiving >= dose
        tv = self.total_volume_cm3
        vpct = 100.0 * cum / tv if tv > 0 else np.zeros_like(cum)
        return d_sorted, vpct

    def cumulative_volume_cm3(self) -> np.ndarray:
        """Cumulative volume (cm^3, NOT %) aligned with self.dose_bins_cgy order
        (i.e. same ordering/indexing as volume_cm3, not re-sorted by dose)."""
        order = np.argsort(self.dose_bins_cgy)
        v_sorted = self.volume_cm3[order]
        cum_sorted = np.cumsum(v_sorted[::-1])[::-1]
        out = np.empty_like(cum_sorted)
        out[order] = cum_sorted
        return out

    def scale_dose(self, factor: float) -> "DVH":
        """Return a new DVH with all dose bins multiplied by `factor`
        (volumes unchanged) -- used for constant-fraction-number dose escalation."""
        return DVH(self.structure_name, self.dose_bins_cgy * factor, self.volume_cm3.copy())

    # ------------------------------------------------------------------ #
    # EQD2 conversion (per-voxel / per-bin), needed before NTCP evaluation
    # ------------------------------------------------------------------ #
    def to_eqd2(self, n_fractions: int, alpha_beta: float) -> "DVH":
        """
        Convert each dose bin (total physical dose delivered in n_fractions)
        to 2 Gy-fraction-equivalent dose (EQD2), using the standard LQ formula:

            EQD2 = D * (d + alpha_beta) / (2 + alpha_beta)

        where d = D / n_fractions is the dose per fraction (cGy).
        """
        if n_fractions <= 0:
            raise ValueError("n_fractions must be > 0")
        d_per_fx = self.dose_bins_cgy / n_fractions
        ab_cgy = alpha_beta * 100.0  # alpha_beta given in Gy -> cGy
        eqd2 = self.dose_bins_cgy * (d_per_fx + ab_cgy) / (200.0 + ab_cgy)
        return DVH(self.structure_name, eqd2, self.volume_cm3.copy())


# ---------------------------------------------------------------------- #
# Import helpers
# ---------------------------------------------------------------------- #
def read_dvh_csv(path: str, structure_name: Optional[str] = None,
                  dose_col: int = 0, volume_col: int = 1,
                  dose_unit: str = "cGy", has_header: bool = True) -> DVH:
    """
    Read a differential DVH from a simple 2-column CSV (dose, volume).
    dose_unit: 'cGy' or 'Gy' -- converted internally to cGy.
    """
    doses, vols = [], []
    with open(path, "r", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    start = 1 if has_header else 0
    for row in rows[start:]:
        if not row or len(row) <= max(dose_col, volume_col):
            continue
        try:
            d = float(row[dose_col])
            v = float(row[volume_col])
        except ValueError:
            continue
        doses.append(d)
        vols.append(v)
    doses = np.array(doses, dtype=float)
    if dose_unit.lower() == "gy":
        doses *= 100.0
    name = structure_name or path.split("/")[-1]
    return DVH(name, doses, np.array(vols, dtype=float))


def read_dicom_rtdose_structure(rtdose_path: str, rtstruct_path: str,
                                 structure_name: str, n_bins: int = 200) -> DVH:
    """
    Compute a differential DVH for one structure directly from a DICOM
    RTDOSE + RTSTRUCT pair. Requires only `pydicom`, `numpy` and
    `matplotlib` -- all already BioSuite-NG dependencies.

    --- Bug-fix history (see BioSuite-NG changelog) ---
    Earlier versions delegated this to
    `rt_utils.RTStructBuilder.create_from(dicom_series_path=None, ...)`.
    That call ALWAYS raised:
        "expected str, bytes or os.PathLike object, not NoneType"
    because rt_utils needs a real folder of CT slices to build the ROI
    mask (internally it calls `os.walk(dicom_series_path)`), and the
    DVH-import dialog only ever asks for the RTDOSE and RTSTRUCT files --
    by design, matching the original BioSuite workflow, there is no CT
    series selection step. Even supplying a CT folder would not have been
    safe: the mask rt_utils returns is shaped like the CT series, not the
    RTDOSE grid, so the subsequent `dose_grid[mask]` indexing could
    silently mismatch shapes.

    A `dicompyler-core`-based rewrite was also tried and rejected: its
    latest published release (0.5.6) still imports `pydicom.dicomio
    .read_file` and `pydicom.pixel_data_handlers`, both removed in modern
    pydicom (this project requires pydicom>=2.4, which resolves to
    pydicom 3.x) -- it fails on import with current pydicom.

    This version instead implements the DVH computation directly, using
    the same well-established algorithm those tools are built on
    (rasterise each RTSTRUCT contour plane onto the RTDOSE pixel grid
    with a point-in-polygon test, XOR-combine multiple contours on the
    same plane to handle holes/rings correctly, then bin the resulting
    per-voxel doses into a volume-weighted histogram). Only the RD/RS
    files the UI already collects are needed -- no CT series, and no
    shape-mismatch risk since every mask is built directly on the dose
    grid.

    Note: like every DVH tool built on this algorithm, this assumes an
    axial-style dose grid (row/column direction cosines along a single
    principal axis each); a clear error is raised for tilted/oblique
    RTDOSE grids rather than silently computing an incorrect DVH.
    """
    import matplotlib.path as mpath
    try:
        import pydicom
    except ImportError as e:
        raise ImportError(
            "DICOM DVH extraction requires 'pydicom'. Install with: pip install pydicom"
        ) from e

    # -- sanity-check the two files before doing any real work, so a
    #    swapped RD/RS selection produces a clear message instead of a
    #    confusing downstream crash --
    try:
        ds_dose = pydicom.dcmread(rtdose_path)
    except Exception as e:
        raise ValueError(f"Could not read the RTDOSE file:\n{rtdose_path}\n\n({e})") from e
    if getattr(ds_dose, "Modality", "") != "RTDOSE":
        raise ValueError(
            f"The file selected as RTDOSE does not look like an RTDOSE "
            f"(Modality = '{getattr(ds_dose, 'Modality', '?')}'). Did you "
            f"swap the RTDOSE and RTSTRUCT file selections?"
        )

    try:
        ds_struct = pydicom.dcmread(rtstruct_path, stop_before_pixels=True)
    except Exception as e:
        raise ValueError(f"Could not read the RTSTRUCT file:\n{rtstruct_path}\n\n({e})") from e
    if getattr(ds_struct, "Modality", "") != "RTSTRUCT":
        raise ValueError(
            f"The file selected as RTSTRUCT does not look like an RTSTRUCT "
            f"(Modality = '{getattr(ds_struct, 'Modality', '?')}'). Did you "
            f"swap the RTDOSE and RTSTRUCT file selections?"
        )

    # -- find the ROI number matching structure_name (case/space-insensitive,
    #    since users retype it by hand) --
    roi_items = list(getattr(ds_struct, "StructureSetROISequence", []))
    roi_number = None
    target = structure_name.strip().casefold()
    for item in roi_items:
        if str(item.ROIName).strip().casefold() == target:
            roi_number = int(item.ROINumber)
            break
    if roi_number is None:
        available = ", ".join(sorted(str(item.ROIName) for item in roi_items))
        raise ValueError(
            f"Structure '{structure_name}' was not found in the RTSTRUCT file.\n"
            f"Available structures: {available or '(none found)'}"
        )

    # -- collect this ROI's CLOSED_PLANAR contours, grouped by z (mm) --
    planes: dict = {}
    for roi_contour in getattr(ds_struct, "ROIContourSequence", []):
        if int(roi_contour.ReferencedROINumber) != roi_number:
            continue
        for c in getattr(roi_contour, "ContourSequence", []):
            if getattr(c, "ContourGeometricType", "CLOSED_PLANAR") != "CLOSED_PLANAR":
                continue  # skip POINT / OPEN_* contours -- not a fillable area
            data = [float(v) for v in c.ContourData]
            if len(data) < 9:  # need >= 3 (x, y, z) points
                continue
            pts_xy = [(data[i], data[i + 1]) for i in range(0, len(data), 3)]
            z = round(data[2], 2)
            planes.setdefault(z, []).append(pts_xy)
    if not planes:
        raise ValueError(
            f"'{structure_name}' has no closed-contour data in the RTSTRUCT file."
        )

    # -- RTDOSE pixel grid geometry --
    if "DoseGridScaling" not in ds_dose:
        raise ValueError("The RTDOSE file is missing DoseGridScaling; cannot convert to physical dose.")
    dose_scaling = float(ds_dose.DoseGridScaling)

    pixel_array = ds_dose.pixel_array
    if pixel_array.ndim == 2:
        pixel_array = pixel_array[np.newaxis, ...]
    n_frames, rows, cols = pixel_array.shape

    ipp = np.array([float(v) for v in ds_dose.ImagePositionPatient], dtype=float)
    iop = [float(v) for v in getattr(ds_dose, "ImageOrientationPatient", [1, 0, 0, 0, 1, 0])]
    row_dir = np.array(iop[0:3])   # direction of increasing COLUMN index
    col_dir = np.array(iop[3:6])   # direction of increasing ROW index
    row_spacing, col_spacing = [float(v) for v in ds_dose.PixelSpacing]  # (row, col) mm

    # Only axis-aligned (non-tilted) in-plane orientations are supported --
    # true of essentially all clinical axial/decubitus RTDOSE grids.
    def _is_axis_aligned(v):
        return np.sum(np.isclose(np.abs(v), 1.0, atol=1e-3)) == 1
    if not (_is_axis_aligned(row_dir) and _is_axis_aligned(col_dir)):
        raise ValueError(
            "This RTDOSE grid uses a tilted/oblique image orientation, which "
            "isn't supported for direct DVH computation. Please use a plan "
            "with a standard axial dose grid."
        )

    if n_frames > 1:
        if "GridFrameOffsetVector" not in ds_dose:
            raise ValueError(
                "This RTDOSE file has multiple frames but no GridFrameOffsetVector; "
                "cannot determine slice positions."
            )
        gfov = [float(v) for v in ds_dose.GridFrameOffsetVector]
    else:
        gfov = [0.0]

    slice_normal = np.cross(row_dir, col_dir)
    frame_z = np.array([(ipp + gfov[i] * slice_normal)[2] for i in range(n_frames)])

    # Physical (X, Y) of every dose-grid pixel centre, as flat arrays for
    # a vectorised point-in-polygon test.
    col_idx = np.arange(cols)
    row_idx = np.arange(rows)
    grid_x = ipp[0] + col_idx[None, :] * col_spacing * row_dir[0] + row_idx[:, None] * row_spacing * col_dir[0]
    grid_y = ipp[1] + col_idx[None, :] * col_spacing * row_dir[1] + row_idx[:, None] * row_spacing * col_dir[1]
    grid_points = np.column_stack([grid_x.ravel(), grid_y.ravel()])

    dose_gy = pixel_array.astype(np.float64) * dose_scaling  # (frames, rows, cols)

    z_min, z_max = float(frame_z.min()), float(frame_z.max())
    z_order = np.argsort(frame_z)
    frame_z_sorted = frame_z[z_order]

    def dose_plane_at(z: float):
        """Nearest dose frame within 0.5 mm, else linear interpolation
        between the two bracketing frames, else None if z is entirely
        outside the dose grid's z-coverage."""
        nearest = int(np.argmin(np.abs(frame_z - z)))
        if abs(frame_z[nearest] - z) < 0.5:
            return dose_gy[nearest]
        if z < z_min or z > z_max:
            return None
        upper = int(np.searchsorted(frame_z_sorted, z))
        lower = upper - 1
        z_lo, z_hi = frame_z_sorted[lower], frame_z_sorted[upper]
        f = (z - z_lo) / (z_hi - z_lo)
        return (1 - f) * dose_gy[z_order[lower]] + f * dose_gy[z_order[upper]]

    # Slice thickness for volume: the structure's OWN plane spacing (the
    # minimum gap between consecutive contour planes), independent of the
    # dose grid's resolution -- matches standard DVH-tool convention.
    sorted_z = sorted(planes.keys())
    gaps = [b - a for a, b in zip(sorted_z[:-1], sorted_z[1:]) if (b - a) > 1e-6]
    if gaps:
        thickness_mm = min(gaps)
    elif len(gfov) > 1:
        thickness_mm = abs(gfov[1] - gfov[0])
    else:
        thickness_mm = float(getattr(ds_dose, "SliceThickness", 1.0) or 1.0)

    voxel_vol_cm3 = (row_spacing * col_spacing * thickness_mm) / 1000.0  # mm^3 -> cm^3

    max_dose_cgy = int(dose_gy.max() * 100) + 1
    hist_cgy = np.zeros(max_dose_cgy)

    for z, polys in planes.items():
        mask = np.zeros(rows * cols, dtype=bool)
        for poly in polys:
            if len(poly) < 3:
                continue
            inside = mpath.Path(poly).contains_points(grid_points)
            mask = np.logical_xor(mask, inside)  # XOR handles holes/rings
        if not mask.any():
            continue
        mask2d = mask.reshape(rows, cols)

        plane = dose_plane_at(z)
        if plane is None:
            # Contour lies entirely outside the dose grid's z-coverage --
            # still count its volume at 0 dose, matching how DVH tools
            # report the full structure volume even where dose is undefined.
            hist_cgy[0] += int(mask2d.sum()) * voxel_vol_cm3
            continue

        dose_cgy_plane = plane * 100.0
        vals = dose_cgy_plane[mask2d]
        idx = np.clip(vals.astype(int), 0, max_dose_cgy - 1)
        np.add.at(hist_cgy, idx, voxel_vol_cm3)

    if hist_cgy.sum() <= 0:
        raise ValueError(
            f"The computed DVH for '{structure_name}' is empty -- its contours "
            f"may not overlap the dose grid, or its contour data could not be read."
        )

    hist_cgy = np.trim_zeros(hist_cgy, trim='b')
    dose_cgy_fine = np.arange(hist_cgy.size) + 0.5  # 1 cGy bin centres
    volume_cm3_fine = hist_cgy

    # Re-bin to `n_bins` evenly spaced bins spanning the dose range, summing
    # volume within each coarser bin (keeps the total structure volume exact
    # -- this only reduces resolution, it never drops or duplicates volume).
    if n_bins and dose_cgy_fine.size > n_bins:
        max_d = float(dose_cgy_fine.max())
        edges = np.linspace(0.0, max_d, n_bins + 1)
        bin_idx = np.clip(np.digitize(dose_cgy_fine, edges) - 1, 0, n_bins - 1)
        volume_out = np.zeros(n_bins)
        np.add.at(volume_out, bin_idx, volume_cm3_fine)
        dose_out = 0.5 * (edges[:-1] + edges[1:])
    else:
        dose_out, volume_out = dose_cgy_fine, volume_cm3_fine

    return DVH(structure_name, dose_out, volume_out)
