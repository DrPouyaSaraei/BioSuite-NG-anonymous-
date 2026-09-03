"""
core/tcp_models.py
Tumour Control Probability models, as used in BioSuite
(Uzan & Nahum, Br J Radiol 2012;85:1279-1286):

  - LQ-Poisson "Marsden" model with accelerated repopulation   [ref 26]
  - LQ-Poisson "Marsden" model + sublethal damage repair (LQ-SLR)
    including the Lea-Catcheside term                           [refs 11, 31]

Both integrate clonogen radiosensitivity heterogeneity via a Gaussian
spread in alpha (parameter `alpha_spread` / sigma_alpha), consistent with
Table 2 of the paper.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
import numpy as np
from scipy import integrate

LN2 = math.log(2.0)


@dataclass
class TCPParams:
    alpha: float                # Gy^-1, mean radiosensitivity
    alpha_beta: float           # Gy
    alpha_spread: float         # Gy^-1, std dev of alpha across clonogens (heterogeneity)
    clonogen_density: float     # cm^-3
    repopulation_delay_days: float = 0.0   # T_k, days before accelerated repopulation starts
    clonogen_doubling_time_days: float = np.inf  # T_d, days (np.inf => no repopulation)


@dataclass
class LQSLRExtra:
    """Extra parameters required by the LQ-SLR model (sublethal damage repair)."""
    mu_repair_per_hour: float   # sublethal damage repair rate constant (h^-1)
    fraction_delivery_min: float  # duration of dose delivery per fraction (minutes)


# ------------------------------------------------------------------------ #
# Survival fraction for a single clonogen sub-population (given alpha)
# ------------------------------------------------------------------------ #
def _survival_fraction_lq(alpha: float, alpha_beta: float, d_per_fx_gy: float,
                           n_fractions: float, g_factor: float = 1.0) -> float:
    """
    Standard LQ cell-survival per fraction, raised to n_fractions:

        S = exp( -n * (alpha*d + beta*g*d^2) )

    g_factor = 1 for instantaneous dose delivery (no protraction correction);
    < 1 when using the Lea-Catcheside G-factor for protracted delivery (LQ-SLR).
    """
    beta = alpha / alpha_beta if alpha_beta > 0 else 0.0
    exponent = -n_fractions * (alpha * d_per_fx_gy + beta * g_factor * d_per_fx_gy ** 2)
    exponent = max(exponent, -700)
    return math.exp(exponent)


def _lea_catcheside_g(mu_per_hour: float, delivery_time_min: float) -> float:
    """
    Lea-Catcheside G-factor for a single continuous exposure of duration T,
    with mono-exponential sublethal-damage repair rate mu (per hour):

        G = (2 / (mu*T)^2) * (mu*T - 1 + exp(-mu*T))

    T supplied in minutes, converted to hours.
    """
    T_h = delivery_time_min / 60.0
    x = mu_per_hour * T_h
    if x < 1e-6:
        return 1.0  # instantaneous-delivery limit
    return (2.0 / x ** 2) * (x - 1.0 + math.exp(-x))


# ------------------------------------------------------------------------ #
# Repopulation correction
# ------------------------------------------------------------------------ #
def _repopulation_log_factor(overall_time_days: float, delay_days: float,
                              doubling_time_days: float) -> float:
    """
    Extra log-cell-kill 'credit' lost to accelerated repopulation, expressed
    as an additive term subtracted from -ln(S) x N0 (i.e. clonogens gained):

        n_effective_doublings = max(0, (T - T_k) / T_d)

    Returns the multiplicative survival-fraction correction factor
    exp(+ln2 * n_effective_doublings) to apply to surviving clonogen number.
    """
    if not np.isfinite(doubling_time_days) or doubling_time_days <= 0:
        return 1.0
    t_prolif = max(0.0, overall_time_days - delay_days)
    n_doublings = t_prolif / doubling_time_days
    return math.exp(LN2 * n_doublings)


# ------------------------------------------------------------------------ #
# Gauss-Hermite style integration over the alpha distribution
# ------------------------------------------------------------------------ #
def _tcp_poisson_heterogeneous(params: TCPParams, total_clonogens: float,
                                d_per_fx_gy: float, n_fractions: float,
                                g_factor: float, overall_time_days: float) -> float:
    """
    TCP = integral over alpha of [ Normal(alpha; mean, sigma) *
                                    exp( -N0 * S(alpha) * repop_factor ) ] dalpha

    following the LQ-Poisson 'Marsden' formalism (Nahum & Sanchez-Nieto 2001).
    """
    mean_a = params.alpha
    sigma_a = params.alpha_spread
    repop_factor = _repopulation_log_factor(
        overall_time_days, params.repopulation_delay_days, params.clonogen_doubling_time_days
    )

    if sigma_a <= 0:
        s = _survival_fraction_lq(mean_a, params.alpha_beta, d_per_fx_gy, n_fractions, g_factor)
        surviving = total_clonogens * s * repop_factor
        return math.exp(-surviving)

    def integrand(a):
        if a <= 0:
            return 0.0
        pdf = (1.0 / (sigma_a * math.sqrt(2 * math.pi))) * math.exp(
            -0.5 * ((a - mean_a) / sigma_a) ** 2
        )
        s = _survival_fraction_lq(a, params.alpha_beta, d_per_fx_gy, n_fractions, g_factor)
        surviving = total_clonogens * s * repop_factor
        return pdf * math.exp(-surviving)

    lo = max(1e-6, mean_a - 6 * sigma_a)
    hi = mean_a + 6 * sigma_a
    val, _ = integrate.quad(integrand, lo, hi, limit=200)
    return float(min(max(val, 0.0), 1.0))


# ======================================================================== #
# Public API
# ======================================================================== #
def tcp_lq_poisson_marsden(gtv_volume_cm3: float, params: TCPParams,
                            total_dose_cgy: float, n_fractions: int,
                            fractions_per_week: float = 5.0) -> float:
    """
    Enhanced 'Marsden' LQ-Poisson TCP model including accelerated repopulation
    (Uzan & Nahum 2012, ref [26]).

    Simplified UNIFORM-dose version: assumes the whole GTV/PTV receives the
    same physical dose (total_dose_cgy over n_fractions). Useful for the
    'constant fraction size/number' dose-escalation curves (Figs 1-2 of the
    paper) where a single dose-multiplication factor is applied. For real
    patient DVHs with spatial non-uniformity, use
    `tcp_lq_poisson_marsden_dvh` instead (see below).
    """
    if n_fractions <= 0:
        return 0.0
    total_clonogens = params.clonogen_density * gtv_volume_cm3
    d_per_fx_gy = (total_dose_cgy / n_fractions) / 100.0
    overall_time_days = (n_fractions / fractions_per_week) * 7.0
    return _tcp_poisson_heterogeneous(
        params, total_clonogens, d_per_fx_gy, float(n_fractions),
        g_factor=1.0, overall_time_days=overall_time_days
    )


def tcp_lq_poisson_marsden_dvh(ptv_dvh, gtv_volume_cm3: float, params: TCPParams,
                                n_fractions: int, fractions_per_week: float = 5.0,
                                g_factor: float = 1.0) -> float:
    """
    DVH-based version of the enhanced 'Marsden' TCP model -- the one
    actually used by BioSuite for real patient plans (see paper, NSCLC
    section): "TCPs are computed using the DVH of the PTV but this is
    assumed to contain the same number of clonogens as the corresponding
    GTV." I.e. total clonogen number N0 = density * GTV_volume, but the
    dose each clonogen sub-population receives follows the (generally
    non-uniform) PTV differential DVH.

    ptv_dvh : DVH
        Differential DVH of the PTV (physical dose in cGy, delivered over
        n_fractions).
    gtv_volume_cm3 : float
        GTV volume -- used ONLY to set the total clonogen number (not the
        dose distribution, which comes from the PTV DVH bins).
    g_factor : float
        Lea-Catcheside protraction factor (1.0 = instantaneous delivery,
        i.e. plain Marsden; < 1.0 for LQ-SLR -- see tcp_lq_slr_dvh, which
        is a thin wrapper around this function that computes g_factor from
        a repair rate + delivery time instead of taking it directly).
    """
    total_volume = ptv_dvh.total_volume_cm3
    if total_volume <= 0 or n_fractions <= 0:
        return 0.0

    total_clonogens = params.clonogen_density * gtv_volume_cm3
    v_frac = ptv_dvh.volume_cm3 / total_volume
    d_per_fx_gy = (ptv_dvh.dose_bins_cgy / n_fractions) / 100.0  # Gy per fraction, per bin
    overall_time_days = (n_fractions / fractions_per_week) * 7.0
    repop_factor = _repopulation_log_factor(
        overall_time_days, params.repopulation_delay_days, params.clonogen_doubling_time_days
    )

    mean_a = params.alpha
    sigma_a = params.alpha_spread

    def mean_survival(a: float) -> float:
        """Volume-weighted mean survival fraction across all PTV dose bins,
        for a given clonogen radiosensitivity alpha."""
        s_per_bin = np.array([
            _survival_fraction_lq(a, params.alpha_beta, d, float(n_fractions), g_factor)
            for d in d_per_fx_gy
        ])
        return float(np.sum(v_frac * s_per_bin))

    if sigma_a <= 0:
        s_mean = mean_survival(mean_a)
        surviving = total_clonogens * s_mean * repop_factor
        return math.exp(-min(surviving, 700))

    def integrand(a):
        if a <= 0:
            return 0.0
        pdf = (1.0 / (sigma_a * math.sqrt(2 * math.pi))) * math.exp(
            -0.5 * ((a - mean_a) / sigma_a) ** 2
        )
        s_mean = mean_survival(a)
        surviving = total_clonogens * s_mean * repop_factor
        return pdf * math.exp(-min(surviving, 700))

    lo = max(1e-6, mean_a - 6 * sigma_a)
    hi = mean_a + 6 * sigma_a
    val, _ = integrate.quad(integrand, lo, hi, limit=200)
    return float(min(max(val, 0.0), 1.0))


def tcp_lq_slr_dvh(ptv_dvh, gtv_volume_cm3: float, params: TCPParams, extra: "LQSLRExtra",
                    n_fractions: int, fractions_per_week: float = 5.0) -> float:
    """
    DVH-based LQ-SLR (LQ-Poisson Marsden + sublethal-damage repair via the
    Lea-Catcheside G-factor). This is the DVH-generalised counterpart of
    tcp_lq_slr, mirroring how tcp_lq_poisson_marsden_dvh generalises
    tcp_lq_poisson_marsden -- added because the UI (Model/Endpoint
    parameters' 'LQ-SLR' option) collected extra.mu_repair_per_hour and
    extra.fraction_delivery_min but NO calculation anywhere ever actually
    used them; every TCP computation silently fell back to the plain
    Marsden formula regardless of which model the user picked.
    """
    g = _lea_catcheside_g(extra.mu_repair_per_hour, extra.fraction_delivery_min)
    return tcp_lq_poisson_marsden_dvh(
        ptv_dvh, gtv_volume_cm3, params, n_fractions, fractions_per_week, g_factor=g
    )


def tcp_lq_slr(gtv_volume_cm3: float, params: TCPParams, extra: LQSLRExtra,
                total_dose_cgy: float, n_fractions: int,
                fractions_per_week: float = 5.0,
                fractions_per_day: int = 1) -> float:
    """
    LQ-SLR: LQ-Poisson Marsden model + sublethal damage repair via the
    Lea-Catcheside G-factor (Dale 1985, ref [11]; Lea & Catcheside 1942, ref [31]).

    As per the paper: the fraction delivery time is adjusted proportionally
    to the fraction size when BioSuite modifies dose per fraction during
    optimisation. Caller is responsible for passing a delivery time already
    scaled if desired; here we accept it as-is via `extra`.
    """
    if n_fractions <= 0:
        return 0.0
    total_clonogens = params.clonogen_density * gtv_volume_cm3
    d_per_fx_gy = (total_dose_cgy / n_fractions) / 100.0
    g = _lea_catcheside_g(extra.mu_repair_per_hour, extra.fraction_delivery_min)

    eff_fractions_per_week = fractions_per_week * fractions_per_day
    overall_time_days = (n_fractions / eff_fractions_per_week) * 7.0

    return _tcp_poisson_heterogeneous(
        params, total_clonogens, d_per_fx_gy, float(n_fractions),
        g_factor=g, overall_time_days=overall_time_days
    )
