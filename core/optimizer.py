"""
core/optimizer.py

Reproduces BioSuite's two optimisation modes (Uzan & Nahum 2012, Methods
section: "BioSuite can optimise in one or two dimensions"):

  1D: for a fixed number of fractions (or fixed fraction size), find the
      total prescription dose that yields a pre-selected NTCP limit on the
      organ(s) at risk.

  2D (isotoxic): for each number of fractions over a chosen range, find the
      highest prescription dose (and corresponding TCP) not exceeding the
      NTCP limit(s). An 'overshoot limit' prevents escalation beyond a TCP
      value (default 99%) at which further dose increase is pointless.

Root-finding uses scipy.optimize.brentq (superset of the derivative-free
Brent approach cited in the original paper, ref [25]).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional
import numpy as np
from scipy.optimize import brentq

from .dvh import DVH
from .ntcp_models import NTCPEndpoint


@dataclass
class NTCPLimit:
    endpoint: NTCPEndpoint
    limit: float  # 0-1


@dataclass
class OneDResult:
    n_fractions: int
    total_dose_cgy: float
    tcp: float
    ntcp_values: dict  # endpoint name -> ntcp
    limiting_endpoint: Optional[str]
    converged: bool


def optimise_1d_fixed_fractions(
    n_fractions: int,
    dvh_by_structure: dict[str, DVH],
    ntcp_limits: list[NTCPLimit],
    tcp_fn: Callable[[float, int], float],  # (total_dose_cgy, n_fractions) -> TCP
    reference_dose_cgy: float,
    dose_search_range_cgy: tuple[float, float] = (100.0, 15000.0),
    overshoot_tcp: float = 0.99,
) -> OneDResult:
    """
    Find the total dose (for a FIXED number of fractions) that brings the
    MOST RESTRICTIVE NTCP endpoint exactly to its limit, then report the
    resulting TCP. If no endpoint is ever limiting within the search range,
    escalate until the overshoot TCP is reached.

    dvh_by_structure must map each NTCP endpoint's target structure name
    to its physical DVH, measured/computed at `reference_dose_cgy` -- in
    practice we scale the DVH by (candidate_dose / reference_dose_cgy)
    inside the root finder, mirroring BioSuite's constant-fraction-number
    DRC (Fig. 1a/2a). `reference_dose_cgy` MUST be the actual total dose
    the supplied DVH corresponds to (e.g. 7400 for a 74 Gy/37# plan) --
    passing the wrong value silently produces a wrong dose scaling.
    """
    lo, hi = dose_search_range_cgy

    def ntcp_at_dose(total_dose_cgy: float, ntcp_limit: NTCPLimit,
                      reference_dose_cgy: float) -> float:
        factor = total_dose_cgy / reference_dose_cgy
        struct = ntcp_limit.endpoint.name  # assume endpoint.name == structure key
        base_dvh = dvh_by_structure[struct]
        scaled = base_dvh.scale_dose(factor)
        return ntcp_limit.endpoint.compute(scaled, n_fractions)

    limiting_dose = hi
    limiting_name = None
    ntcp_at_limiting = {}

    for nl in ntcp_limits:
        def f(d, nl=nl):
            return ntcp_at_dose(d, nl, reference_dose_cgy) - nl.limit
        f_lo, f_hi = f(lo), f(hi)
        if f_lo > 0:
            # even the lowest dose in range exceeds the limit -> infeasible
            candidate_dose = lo
        elif f_hi < 0:
            # limit never reached in range -> not limiting within range
            candidate_dose = hi
        else:
            candidate_dose = brentq(f, lo, hi, xtol=1.0)
        if candidate_dose < limiting_dose:
            limiting_dose = candidate_dose
            limiting_name = nl.endpoint.name

    # apply overshoot limit: don't escalate past TCP = overshoot_tcp
    def tcp_minus_overshoot(d):
        return tcp_fn(d, n_fractions) - overshoot_tcp

    converged = True
    if tcp_fn(limiting_dose, n_fractions) >= overshoot_tcp:
        # find where TCP first reaches overshoot, use that instead
        try:
            if tcp_minus_overshoot(lo) >= 0:
                limiting_dose = lo
            else:
                limiting_dose = brentq(tcp_minus_overshoot, lo, limiting_dose, xtol=1.0)
            limiting_name = "overshoot_limit"
        except ValueError:
            converged = False

    final_ntcp = {}
    for nl in ntcp_limits:
        final_ntcp[nl.endpoint.name] = ntcp_at_dose(limiting_dose, nl, reference_dose_cgy)

    return OneDResult(
        n_fractions=n_fractions,
        total_dose_cgy=limiting_dose,
        tcp=tcp_fn(limiting_dose, n_fractions),
        ntcp_values=final_ntcp,
        limiting_endpoint=limiting_name,
        converged=converged,
    )


@dataclass
class IsotoxicPoint:
    n_fractions: int
    total_dose_cgy: float
    tcp: float
    limiting_endpoint: Optional[str]
    hit_overshoot: bool


def optimise_2d_isotoxic(
    fraction_range: range,
    dvh_by_structure: dict[str, DVH],
    ntcp_limits: list[NTCPLimit],
    tcp_fn: Callable[[float, int], float],
    reference_dose_cgy: float,
    dose_search_range_cgy: tuple[float, float] = (100.0, 20000.0),
    overshoot_tcp: float = 0.99,
) -> list[IsotoxicPoint]:
    """
    2D isotoxic optimisation (BioSuite's core feature): for each number of
    fractions in `fraction_range`, find the highest total dose not exceeding
    ANY of the supplied NTCP limits, and evaluate the resulting TCP.

    Reproduces the curves in Figures 3, 4 and 5 of Uzan & Nahum (2012).
    Points are flagged 'hit_overshoot' (paper: shown in green) vs limited by
    an NTCP constraint (paper: shown in red).
    """
    lo, hi = dose_search_range_cgy
    results = []

    for nfx in fraction_range:
        limiting_dose = hi
        limiting_name = None

        for nl in ntcp_limits:
            struct = nl.endpoint.name

            def f(d, nl=nl, struct=struct, nfx=nfx):
                factor = d / reference_dose_cgy
                scaled = dvh_by_structure[struct].scale_dose(factor)
                return nl.endpoint.compute(scaled, nfx) - nl.limit

            f_lo, f_hi = f(lo), f(hi)
            if f_lo > 0:
                candidate = lo
            elif f_hi < 0:
                candidate = hi
            else:
                candidate = brentq(f, lo, hi, xtol=1.0)
            if candidate < limiting_dose:
                limiting_dose = candidate
                limiting_name = nl.endpoint.name

        hit_overshoot = False
        tcp_val = tcp_fn(limiting_dose, nfx)
        if tcp_val >= overshoot_tcp:
            def g(d, nfx=nfx):
                return tcp_fn(d, nfx) - overshoot_tcp
            try:
                if g(lo) >= 0:
                    limiting_dose = lo
                else:
                    limiting_dose = brentq(g, lo, limiting_dose, xtol=1.0)
                limiting_name = "overshoot_limit"
                hit_overshoot = True
                tcp_val = tcp_fn(limiting_dose, nfx)
            except ValueError:
                pass

        results.append(IsotoxicPoint(
            n_fractions=nfx,
            total_dose_cgy=limiting_dose,
            tcp=tcp_val,
            limiting_endpoint=limiting_name,
            hit_overshoot=hit_overshoot,
        ))

    return results


# ======================================================================== #
# *** NEW: hooks toward inverse-planning-style objective (extension) ***
# The paper explicitly flags this as future work:
#   "Ideally, inverse planning based on radiobiological criteria [46, 47]
#    could yield true radiobiologically optimal plans which, by definition,
#    could not be further improved in BioSuite."
# The function below does not replan beams -- it exposes a differentiable-ish
# scalar objective (TCP - penalty*sum(NTCP overages)) that a TPS-side inverse
# planner (or a segment-weight optimiser working on multiple candidate DVH
# realisations) could consume as its biological cost function.
# ======================================================================== #
def radiobiological_objective(
    total_dose_cgy: float,
    n_fractions: int,
    dvh_by_structure: dict[str, DVH],
    ntcp_limits: list[NTCPLimit],
    tcp_fn: Callable[[float, int], float],
    reference_dose_cgy: float,
    ntcp_penalty_weight: float = 50.0,
) -> float:
    """Scalar objective = TCP - weight * sum(max(0, NTCP - limit))."""
    tcp_val = tcp_fn(total_dose_cgy, n_fractions)
    penalty = 0.0
    factor = total_dose_cgy / reference_dose_cgy
    for nl in ntcp_limits:
        scaled = dvh_by_structure[nl.endpoint.name].scale_dose(factor)
        ntcp_val = nl.endpoint.compute(scaled, n_fractions)
        penalty += max(0.0, ntcp_val - nl.limit)
    return tcp_val - ntcp_penalty_weight * penalty
