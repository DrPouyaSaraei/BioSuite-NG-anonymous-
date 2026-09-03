"""
core/confidence.py

*** NEW FEATURE (not present in the original BioSuite v12.2) ***

The original paper explicitly lists this as a limitation:
    "In its current state, BioSuite does not include any confidence interval
    calculations on NTCP and TCP or as a function of fraction number."
    (Discussion section, referencing Schilstra & Meertens 2001 [ref 48])

This module adds Monte-Carlo propagation of parameter uncertainty through
the NTCP/TCP models to produce confidence intervals, using the standard
approach: repeatedly sample each model parameter from an assumed
distribution (Normal by default, truncated to physically valid ranges),
recompute NTCP/TCP, and report percentiles of the resulting distribution.

This does NOT require patient-level outcome data (which the paper notes
is impractical to gather) -- instead it uses reported parameter
uncertainties (e.g. standard errors from the literature fits, such as
Table 1/2 of the paper), which is the pragmatic middle ground the authors
themselves point toward for future work.
"""

from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Callable, Sequence
import numpy as np


@dataclass
class ParamUncertainty:
    """Uncertainty specification for one scalar parameter of a model."""
    name: str
    mean: float
    sd: float
    lower_bound: float = -np.inf
    upper_bound: float = np.inf

    def sample(self, rng: np.random.Generator, size: int) -> np.ndarray:
        s = rng.normal(self.mean, self.sd, size=size)
        return np.clip(s, self.lower_bound, self.upper_bound)


def monte_carlo_ci(
    compute_fn: Callable[..., float],
    param_uncertainties: Sequence[ParamUncertainty],
    fixed_kwargs: dict,
    n_samples: int = 5000,
    ci: float = 0.95,
    seed: int | None = None,
) -> dict:
    """
    Propagate parameter uncertainty through an arbitrary NTCP/TCP compute
    function via Monte Carlo sampling.

    Parameters
    ----------
    compute_fn : callable
        A function taking keyword arguments (including the sampled
        parameter names) and returning a single float (NTCP or TCP, 0-1).
    param_uncertainties : sequence of ParamUncertainty
        One entry per uncertain parameter; `compute_fn` must accept a
        keyword argument matching each `.name`.
    fixed_kwargs : dict
        Any other keyword arguments compute_fn needs that are NOT being
        varied (e.g. the DVH object, n_fractions, geometry).
    n_samples : int
        Number of Monte Carlo draws (default 5000; increase for smoother tails).
    ci : float
        Confidence level (default 0.95 -> 2.5/97.5 percentiles).

    Returns
    -------
    dict with keys: 'median', 'mean', 'lower', 'upper', 'samples' (ndarray)
    """
    rng = np.random.default_rng(seed)
    samples = np.empty(n_samples)

    sampled_values = {
        pu.name: pu.sample(rng, n_samples) for pu in param_uncertainties
    }

    for i in range(n_samples):
        kwargs = dict(fixed_kwargs)
        for name, arr in sampled_values.items():
            kwargs[name] = arr[i]
        try:
            samples[i] = compute_fn(**kwargs)
        except Exception:
            samples[i] = np.nan

    valid = samples[~np.isnan(samples)]
    alpha = 1.0 - ci
    lower_pct = 100 * (alpha / 2)
    upper_pct = 100 * (1 - alpha / 2)

    return {
        "median": float(np.median(valid)) if valid.size else float("nan"),
        "mean": float(np.mean(valid)) if valid.size else float("nan"),
        "lower": float(np.percentile(valid, lower_pct)) if valid.size else float("nan"),
        "upper": float(np.percentile(valid, upper_pct)) if valid.size else float("nan"),
        "ci_level": ci,
        "n_valid": int(valid.size),
        "n_total": n_samples,
        "samples": valid,
    }


def tornado_sensitivity(
    compute_fn: Callable[..., float],
    param_uncertainties: Sequence[ParamUncertainty],
    fixed_kwargs: dict,
) -> dict:
    """
    *** NEW FEATURE ***
    One-at-a-time sensitivity ("tornado") analysis: for each uncertain
    parameter, vary ONLY that parameter by +/-1 SD (holding every other
    parameter at its mean) and record the resulting NTCP/TCP swing, with
    all other parameters fixed at their mean values.

    This complements monte_carlo_ci (which varies ALL parameters
    simultaneously to get an overall CI) by showing WHICH parameter
    individually drives most of that uncertainty -- the classic
    "tornado diagram" used in sensitivity/decision analysis.

    Returns
    -------
    dict with:
      'base'  : output with every parameter at its mean
      'rows'  : list of dicts, one per parameter, SORTED by descending
                |swing| (largest driver first -- the conventional tornado
                ordering), each with:
                  name, low_value, high_value, low_output, high_output, swing
    """
    means = {pu.name: pu.mean for pu in param_uncertainties}
    base = compute_fn(**fixed_kwargs, **means)

    rows = []
    for pu in param_uncertainties:
        kwargs_low = dict(fixed_kwargs, **means)
        kwargs_high = dict(fixed_kwargs, **means)
        low_val = max(pu.mean - pu.sd, pu.lower_bound)
        high_val = min(pu.mean + pu.sd, pu.upper_bound)
        kwargs_low[pu.name] = low_val
        kwargs_high[pu.name] = high_val
        try:
            out_low = compute_fn(**kwargs_low)
        except Exception:
            out_low = float("nan")
        try:
            out_high = compute_fn(**kwargs_high)
        except Exception:
            out_high = float("nan")
        rows.append({
            "name": pu.name,
            "low_value": low_val, "high_value": high_val,
            "low_output": out_low, "high_output": out_high,
            "swing": abs(out_high - out_low) if not (np.isnan(out_low) or np.isnan(out_high)) else 0.0,
        })

    rows.sort(key=lambda r: r["swing"], reverse=True)
    return {"base": base, "rows": rows}


def curve_with_ci(
    x_values: Sequence[float],
    compute_fn_factory: Callable[[float], Callable[..., float]],
    param_uncertainties: Sequence[ParamUncertainty],
    fixed_kwargs: dict,
    n_samples: int = 2000,
    ci: float = 0.95,
    seed: int | None = None,
) -> dict:
    """
    Convenience wrapper to build a full NTCP-vs-x or TCP-vs-x curve (e.g.
    vs number of fractions, as in Figures 1-5 of the paper) WITH a
    confidence band at every point.

    compute_fn_factory(x) must return a compute_fn suitable for monte_carlo_ci
    at that particular x (e.g. bakes in n_fractions=x).
    """
    medians, lowers, uppers = [], [], []
    rng_seed = seed
    for x in x_values:
        fn = compute_fn_factory(x)
        result = monte_carlo_ci(
            fn, param_uncertainties, fixed_kwargs,
            n_samples=n_samples, ci=ci, seed=rng_seed
        )
        medians.append(result["median"])
        lowers.append(result["lower"])
        uppers.append(result["upper"])
    return {
        "x": np.asarray(x_values),
        "median": np.asarray(medians),
        "lower": np.asarray(lowers),
        "upper": np.asarray(uppers),
    }
