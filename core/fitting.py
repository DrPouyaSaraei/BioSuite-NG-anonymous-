"""
core/fitting.py

Parameter fitting: given a set of (total_dose_cgy, n_fractions, volume_cm3,
outcome 0/1) clinical data points, fit the TCP model's `alpha` parameter
(other TCPParams fields held fixed) by maximum likelihood -- mirrors the
original BioSuite "Fitting" tab (Model: Marsden; Fitting equation:
ChiSq / Binomial / Bernoulli).

Only `alpha` is fitted (1-parameter fit) since that's the most clinically
identifiable single parameter from local-control outcome data with the
sample sizes typically available; alpha_beta, alpha_spread and clonogen
density are assumed fixed at literature values, consistent with how the
paper itself fixes these tables and only varies alpha/alpha_beta as a
scenario, not as a per-patient-cohort fit.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
import numpy as np
from scipy.optimize import minimize_scalar

from .tcp_models import TCPParams, tcp_lq_poisson_marsden


@dataclass
class FitEntry:
    label: str
    total_dose_cgy: float
    n_fractions: int
    volume_cm3: float
    outcome: int  # 0 or 1 (local control observed / not observed)


@dataclass
class FitResult:
    fitted_alpha: float
    neg_log_likelihood: float
    n_entries: int
    equation: str
    predicted_tcp: list[float]


def _predict(entries: list[FitEntry], base_params: TCPParams, alpha: float) -> np.ndarray:
    params = replace(base_params, alpha=alpha)
    preds = np.array([
        tcp_lq_poisson_marsden(e.volume_cm3, params, e.total_dose_cgy, e.n_fractions)
        for e in entries
    ])
    return np.clip(preds, 1e-6, 1 - 1e-6)


def _bernoulli_nll(entries: list[FitEntry], base_params: TCPParams, alpha: float) -> float:
    p = _predict(entries, base_params, alpha)
    y = np.array([e.outcome for e in entries], dtype=float)
    return float(-np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))


def _chisq(entries: list[FitEntry], base_params: TCPParams, alpha: float) -> float:
    p = _predict(entries, base_params, alpha)
    y = np.array([e.outcome for e in entries], dtype=float)
    return float(np.sum((y - p) ** 2 / (p * (1 - p))))


def _binomial_nll(entries: list[FitEntry], base_params: TCPParams, alpha: float) -> float:
    # same functional form as Bernoulli for individual-patient (n=1) entries;
    # kept as a distinct named option for parity with the original UI, where
    # it would differ if entries represented grouped (n>1) cohorts.
    return _bernoulli_nll(entries, base_params, alpha)


EQUATIONS = {
    "Bernoulli": _bernoulli_nll,
    "Binomial": _binomial_nll,
    "ChiSq": _chisq,
}


def fit_alpha(entries: list[FitEntry], base_params: TCPParams,
              equation: str = "Bernoulli",
              alpha_bounds: tuple[float, float] = (0.01, 1.0)) -> FitResult:
    if not entries:
        raise ValueError("Need at least one data entry to fit")
    objective_fn = EQUATIONS.get(equation, _bernoulli_nll)

    res = minimize_scalar(
        lambda a: objective_fn(entries, base_params, a),
        bounds=alpha_bounds, method="bounded",
    )
    fitted_alpha = float(res.x)
    final_score = float(res.fun)
    preds = _predict(entries, base_params, fitted_alpha).tolist()
    return FitResult(
        fitted_alpha=fitted_alpha, neg_log_likelihood=final_score,
        n_entries=len(entries), equation=equation, predicted_tcp=preds,
    )
