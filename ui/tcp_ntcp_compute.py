"""
ui/tcp_ntcp_compute.py
Single shared dispatcher for "compute TCP for this endpoint+DVH", used by
every tab that needs a TCP number (DVH plots, DRC, Optimisation, Export).

This exists specifically to fix a real bug: four different call sites
each called core.tcp_models.tcp_lq_poisson_marsden_dvh directly, so when
an endpoint's model was "LQ-SLR" (with its own mu_repair_per_hour /
fraction_delivery_min parameters collected in the Add-endpoint dialog),
those extra parameters were silently ignored everywhere -- every TCP
number in the app was actually plain Marsden, regardless of which model
the user picked. Routing every call site through this one function means
fixing the dispatch logic here fixes it everywhere, and any FUTURE TCP
model added only needs to be wired up in one place.
"""
from __future__ import annotations

from core.dvh import DVH
from core.tcp_models import tcp_lq_poisson_marsden_dvh, tcp_lq_slr_dvh


def compute_tcp(ep, dvh: DVH, n_fractions: int) -> float:
    """ep is a ui.app_state.EndpointDefinition with kind == 'TCP'."""
    gtv_vol = ep.gtv_volume_cm3 or dvh.total_volume_cm3
    if ep.model == "LQ-SLR" and ep.lq_slr_extra is not None:
        return tcp_lq_slr_dvh(dvh, gtv_vol, ep.tcp_params, ep.lq_slr_extra, n_fractions)
    return tcp_lq_poisson_marsden_dvh(dvh, gtv_vol, ep.tcp_params, n_fractions)
