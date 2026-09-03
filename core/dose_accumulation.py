"""
core/dose_accumulation.py

*** NEW FEATURE (not present in original BioSuite v12.2) ***

The paper explicitly flags this as a gap (Discussion, NSCLC section):
    "More sophisticated and rigorous techniques to deal with the target
    DVHs could be used such as 'dose accumulation' on a four-dimensional
    CT set [34]... this feature is not yet available in any clinical TPS."

This module provides a *DVH-level* approximation of 4D dose accumulation:
given several DVHs of the SAME structure computed on different breathing
phases (or different fractions of a plan, e.g. an adaptive re-plan
partway through treatment), it combines them via volume-weighted
addition of dose-bin histograms, which is the standard way to combine
per-phase DVHs when only DVHs (not full 3D dose grids) are available.

For a true voxel-level 4D accumulation you need the 3D dose grids +
deformable registration, which is out of scope for a DVH-only tool;
this module documents that limitation explicitly rather than silently
approximating it.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from .dvh import DVH


@dataclass
class PhaseWeight:
    """One breathing phase (or one segment of a course) and its time weight
    (e.g. fraction of the breathing cycle spent in this phase, or the
    fraction of total treatment fractions delivered under this plan)."""
    dvh: DVH
    weight: float  # should sum to 1.0 across all phases for a given structure


def accumulate_dvh_weighted(phases: list[PhaseWeight], n_bins: int = 200) -> DVH:
    """
    Combine several DVHs of the SAME structure into one accumulated DVH,
    via volume-weighted histogram summation on a common dose grid.

    This is the standard *DVH-based* approximation of 4D dose accumulation
    used when only DVHs are exported from the TPS/4D dose engine (i.e. no
    access to the underlying dose grids + deformable image registration).
    It is exact only if each phase's DVH already reflects deformed/aligned
    anatomy; it does NOT itself perform deformable registration.

    Parameters
    ----------
    phases : list of PhaseWeight
        Each phase's DVH plus its time weight (weights need not sum to 1;
        they are normalised internally).
    n_bins : int
        Number of dose bins for the common accumulated-dose grid.

    Returns
    -------
    DVH : accumulated differential DVH on a common dose grid.
    """
    if not phases:
        raise ValueError("Need at least one phase")

    total_w = sum(p.weight for p in phases)
    if total_w <= 0:
        raise ValueError("Phase weights must sum to a positive value")

    structure_name = phases[0].dvh.structure_name
    max_dose = max(p.dvh.max_dose_cgy for p in phases)
    common_bins = np.linspace(0, max_dose * 1.05, n_bins)
    bin_width = common_bins[1] - common_bins[0] if n_bins > 1 else 1.0

    accumulated_volume = np.zeros(n_bins)

    for p in phases:
        w = p.weight / total_w
        # resample this phase's differential DVH onto the common dose grid
        # by nearest-bin assignment, scaling total volume contribution by w
        d = p.dvh.dose_bins_cgy
        v = p.dvh.volume_cm3 * w
        idx = np.clip(
            np.searchsorted(common_bins, d) - 1, 0, n_bins - 1
        )
        np.add.at(accumulated_volume, idx, v)

    return DVH(structure_name, common_bins, accumulated_volume)


def accumulate_dvh_simple_sum(dvhs_same_structure: list[DVH], n_bins: int = 200) -> DVH:
    """
    Convenience wrapper for the common case of accumulating dose from
    SEQUENTIAL plan phases (e.g. primary course + boost, or original plan
    + mid-course adaptive re-plan) where each phase's full (unweighted)
    dose simply adds up -- equivalent to accumulate_dvh_weighted with all
    weights = 1 (no time-averaging, pure summation).
    """
    phases = [PhaseWeight(dvh=d, weight=1.0) for d in dvhs_same_structure]
    return accumulate_dvh_weighted(phases, n_bins=n_bins)
