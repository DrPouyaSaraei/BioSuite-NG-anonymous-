"""
core/ntcp_models.py
Normal Tissue Complication Probability models, as used in BioSuite
(Uzan & Nahum, Br J Radiol 2012;85:1279-1286):

  - Lyman-Kutcher-Burman (LKB)              [refs 8,9,27-30 in the paper]
  - Relative Seriality (Kallman)            [ref 10]
  - Simple Maximum Dose (SMD, sigmoid)      [defined explicitly in the paper]

All models operate on an EQD2-converted differential DVH (see core.dvh.DVH.to_eqd2).
"""

from __future__ import annotations
import math
from dataclasses import dataclass
import numpy as np
from scipy.stats import norm
from scipy import integrate

from .dvh import DVH
from .ntcp_niemierko import NiemierkoEUDParams, ntcp_niemierko


# ======================================================================== #
# 1. Lyman-Kutcher-Burman (LKB)
# ======================================================================== #
@dataclass
class LKBParams:
    td50: float      # cGy, EQD2, for uniform whole-organ irradiation
    m: float          # slope parameter
    n: float          # volume-effect parameter (n->1 parallel, n->0 serial)
    alpha_beta: float  # Gy, for EQD2 conversion


def _generalised_eud(eqd2_dvh: DVH, n: float) -> float:
    """
    Compute the generalised Equivalent Uniform Dose (Niemierko 1999 formalism,
    used internally by the LKB effective-volume method):

        gEUD = ( sum_i v_i * D_i^(1/n) ) ^ n

    where v_i is the *fractional* volume in bin i and D_i the EQD2 dose.
    """
    tv = eqd2_dvh.total_volume_cm3
    if tv <= 0:
        return 0.0
    v_frac = eqd2_dvh.volume_cm3 / tv
    # guard against zero dose bins raised to negative/fractional powers
    d = np.clip(eqd2_dvh.dose_bins_cgy, 1e-6, None)
    if n <= 0:
        # serial limit: gEUD -> max dose
        return float(np.max(d[eqd2_dvh.volume_cm3 > 0])) if (eqd2_dvh.volume_cm3 > 0).any() else 0.0
    inner = np.sum(v_frac * d ** (1.0 / n))
    return float(inner ** n)


def ntcp_lkb(eqd2_dvh: DVH, params: LKBParams) -> float:
    """
    NTCP via the Lyman model evaluated at the effective (generalised EUD) dose:

        NTCP = Phi( (gEUD - TD50) / (m * TD50) )

    where Phi is the standard normal CDF.
    """
    geud = _generalised_eud(eqd2_dvh, params.n)
    if params.m <= 0 or params.td50 <= 0:
        raise ValueError("LKB parameters m and td50 must be positive")
    t = (geud - params.td50) / (params.m * params.td50)
    return float(norm.cdf(t))


# ======================================================================== #
# 2. Relative Seriality (Kallman, Agren, Brahme 1992)
# ======================================================================== #
@dataclass
class RelSerialityParams:
    d50: float        # cGy, EQD2, dose for 50% complication at uniform irradiation
    gamma50: float     # normalised dose-response gradient at D50
    s: float           # relative seriality parameter (0 < s <= 1; 1 = fully serial)


def _p_i(d_cgy: float, params: RelSerialityParams) -> float:
    """Single-voxel/bin complication probability at dose d_cgy (Poisson-based)."""
    d50 = params.d50
    g50 = params.gamma50
    if d50 <= 0:
        return 0.0
    exponent = g50 * math.e * (1.0 - d_cgy / d50)
    # avoid overflow
    exponent = max(min(exponent, 700), -700)
    return 2.0 ** (-math.exp(exponent))


def ntcp_relative_seriality(eqd2_dvh: DVH, params: RelSerialityParams) -> float:
    """
    Relative seriality NTCP model:

        NTCP = [ 1 - prod_i (1 - P_i^s)^(v_i) ] ^ (1/s)

    where v_i is the fractional volume in bin i and P_i is the response of
    a fully serial sub-unit to the (EQD2) dose in that bin.
    """
    tv = eqd2_dvh.total_volume_cm3
    if tv <= 0:
        return 0.0
    s = params.s
    v_frac = eqd2_dvh.volume_cm3 / tv
    log_prod = 0.0
    for d, v in zip(eqd2_dvh.dose_bins_cgy, v_frac):
        if v <= 0:
            continue
        p_i = _p_i(float(d), params)
        p_i = min(max(p_i, 1e-12), 1 - 1e-12)
        log_prod += v * math.log(1.0 - p_i ** s)
    inner = 1.0 - math.exp(log_prod)
    inner = min(max(inner, 0.0), 1.0)
    return float(inner ** (1.0 / s))


# ======================================================================== #
# 3. Simple Maximum Dose (SMD) -- sigmoid, as defined explicitly in the paper
# ======================================================================== #
@dataclass
class SMDParams:
    d_lim: float       # cGy, EQD2 threshold dose for this complication
    alpha_beta: float   # Gy, used upstream for EQD2 conversion


def ntcp_smd(eqd2_dvh: DVH, params: SMDParams) -> float:
    """
    NTCP = 1 / (1 + exp(-(Dmax - Dlim)))

    Dmax is the EQD2 maximum dose (cGy) from the DVH; Dlim is the threshold (cGy).
    This is the exact sigmoid form given in Uzan & Nahum (2012), eq. in the
    'Radiobiological models' section.
    """
    d_max = eqd2_dvh.max_dose_cgy
    exponent = -(d_max - params.d_lim)
    exponent = max(min(exponent, 700), -700)
    return float(1.0 / (1.0 + math.exp(exponent)))


# ======================================================================== #
# Unified endpoint wrapper
# ======================================================================== #
@dataclass
class NTCPEndpoint:
    """
    A named NTCP end point bundling: which model, its parameters, and the
    alpha/beta used for the EQD2 conversion of the relevant DVH.
    """
    name: str
    model: str  # 'LKB' | 'RS' | 'SMD' | 'EUD'  ('EUD' is a new addition, see ntcp_niemierko.py)
    alpha_beta: float
    params: LKBParams | RelSerialityParams | SMDParams | NiemierkoEUDParams

    def compute(self, physical_dvh: DVH, n_fractions: int) -> float:
        eqd2_dvh = physical_dvh.to_eqd2(n_fractions, self.alpha_beta)
        if self.model == "LKB":
            return ntcp_lkb(eqd2_dvh, self.params)
        elif self.model == "RS":
            return ntcp_relative_seriality(eqd2_dvh, self.params)
        elif self.model == "SMD":
            return ntcp_smd(eqd2_dvh, self.params)
        elif self.model == "EUD":
            return ntcp_niemierko(eqd2_dvh, self.params)
        else:
            raise ValueError(f"Unknown NTCP model '{self.model}'")
