"""
core/ntcp_niemierko.py

*** NEW MODEL (not present in original BioSuite v12.2) ***

EUD-based NTCP model of Niemierko (1999) / Luxton, Keall & King (2008),
cited in the paper's reference list [29, 30] but NOT implemented as a
selectable end-point model in BioSuite itself (BioSuite only offers LKB,
Relative Seriality and SMD). We add it here as an additional, optional
model the user can select per end point.

    gEUD = ( sum_i v_i * D_i^a ) ^ (1/a)

    NTCP = 1 / (1 + (TD50 / gEUD)^(4*gamma50))

a is Niemierko's volume parameter (a<0 for serial-like organs, a>0 for
parallel-like organs -- opposite sign convention from the LKB 'n', where
a = 1/n approximately for a>0 organs). gamma50 controls the slope at D50.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
import numpy as np

from .dvh import DVH


@dataclass
class NiemierkoEUDParams:
    a: float          # Niemierko volume parameter (organ-specific, literature-fitted)
    td50: float        # cGy, EQD2, dose giving 50% complication for uniform irradiation
    gamma50: float      # normalised dose-response gradient at D50


def niemierko_geud(eqd2_dvh: DVH, a: float) -> float:
    """
    Generalised Equivalent Uniform Dose:
        gEUD = ( sum_i v_i * D_i^a ) ^ (1/a)
    v_i = fractional volume in bin i, D_i = EQD2 dose (cGy).
    a -> +inf recovers Dmax; a -> -inf recovers Dmin; a=1 recovers mean dose.
    """
    tv = eqd2_dvh.total_volume_cm3
    if tv <= 0:
        return 0.0
    v_frac = eqd2_dvh.volume_cm3 / tv
    d = np.clip(eqd2_dvh.dose_bins_cgy, 1e-6, None)
    if abs(a) < 1e-9:
        # geometric-mean limit
        return float(np.exp(np.sum(v_frac * np.log(d))))
    inner = np.sum(v_frac * d ** a)
    if inner <= 0:
        return 0.0
    return float(inner ** (1.0 / a))


def ntcp_niemierko(eqd2_dvh: DVH, params: NiemierkoEUDParams) -> float:
    """NTCP = 1 / (1 + (TD50/gEUD)^(4*gamma50))."""
    geud = niemierko_geud(eqd2_dvh, params.a)
    if geud <= 0:
        return 0.0
    ratio = params.td50 / geud
    exponent = 4.0 * params.gamma50
    try:
        val = 1.0 / (1.0 + ratio ** exponent)
    except OverflowError:
        val = 0.0 if ratio > 1 else 1.0
    return float(min(max(val, 0.0), 1.0))
