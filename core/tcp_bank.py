"""
core/tcp_bank.py
Loader and helper queries for data/tcp_parameter_bank.json -- the curated,
multi-source Target/Poisson TCP parameter bank (see build_tcp_bank.py).

Mirrors core/lkb_bank.py's design: multiple citable parameter sets per
tumour site/endpoint, `selectable` gating for records BioSuite-NG's
engine cannot faithfully reproduce, and STRICT separation between
`clonogen_density_percc` and `total_clonogens_k` (never silently
converted one to the other -- see build_tcp_bank.py's module docstring).
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass
from typing import Optional

from core.paths import resource_path

BANK_PATH = resource_path("data", "tcp_parameter_bank.json")


@dataclass
class TCPBankEntry:
    record_id: str
    tumour_site: str
    histology_setting: str
    modality_schedule: str
    model_family_raw: str
    model_family_key: str   # poisson_lq_repopulation | lq_protraction_repair | alpha_beta_evidence_only | zaider_minerbo | ...
    endpoint: str
    label: str
    alpha_definition: str
    alpha_per_gy: Optional[float]
    alpha_value_status: str
    alpha_spread_sd: Optional[float]
    alpha_beta_gy: Optional[float]
    clonogen_density_percc: Optional[float]
    total_clonogens_k: Optional[float]
    k_fixed_no_reference_volume: bool
    repopulation_as_reported: str
    repopulation_days_tpot: Optional[float]
    repopulation_rate_per_day: Optional[float]
    derived_mapping_basis: str
    delay_before_repopulation_days: Optional[float]
    repair_halftime_min: Optional[float]
    sublethal_repair_mu_per_min: Optional[float]
    fraction_duration_correction: str
    status: str
    selectable: bool
    source: str
    url: Optional[str]
    notes: str

    @property
    def reports_density(self) -> bool:
        return self.clonogen_density_percc is not None

    @property
    def reports_total_k(self) -> bool:
        return self.total_clonogens_k is not None

    @property
    def missing_fields(self) -> list[str]:
        """Fields BioSuite-NG needs that this record does NOT report --
        the 'Add from TCP parameter bank' dialog must require the user to
        fill these in explicitly before the endpoint can be used."""
        missing = []
        if self.alpha_spread_sd is None:
            missing.append("alpha_spread_sd")
        if not self.reports_density and not self.reports_total_k:
            missing.append("clonogen_density_or_total_k")
        if self.repopulation_days_tpot is None and self.model_family_key != "alpha_beta_evidence_only":
            missing.append("repopulation_days")
        return missing


_cache: list[TCPBankEntry] | None = None


def load_bank(path: str = BANK_PATH) -> list[TCPBankEntry]:
    global _cache
    if _cache is not None and path == BANK_PATH:
        return _cache
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"TCP parameter bank not found at:\n{path}\n\n"
            "If you're running the packaged .exe, rebuild it with build_exe.bat "
            "(which bundles the data/ folder)."
        )
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    entries = [TCPBankEntry(**r) for r in raw]
    if path == BANK_PATH:
        _cache = entries
    return entries


def get_sites(entries: list[TCPBankEntry] | None = None, selectable_only: bool = True) -> list[str]:
    entries = entries if entries is not None else load_bank()
    return sorted({e.tumour_site for e in entries if (e.selectable or not selectable_only)})


def get_endpoints(site: str, entries: list[TCPBankEntry] | None = None,
                   selectable_only: bool = True) -> list[str]:
    entries = entries if entries is not None else load_bank()
    return sorted({e.endpoint for e in entries
                   if e.tumour_site == site and (e.selectable or not selectable_only)})


def get_parameter_sets(site: str, endpoint: str,
                        entries: list[TCPBankEntry] | None = None,
                        selectable_only: bool = True) -> list[TCPBankEntry]:
    entries = entries if entries is not None else load_bank()
    return [e for e in entries if e.tumour_site == site and e.endpoint == endpoint
            and (e.selectable or not selectable_only)]
