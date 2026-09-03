"""
core/lkb_bank.py
Loader and helper queries for data/lkb_parameter_bank.json -- the curated,
English-language, multi-source LKB parameter bank (built from the user's
evidence review, see build_ntcp_bank_v2.py). Supports multiple citable
parameter sets per organ/endpoint (selectable by "Author et al. Year"),
and flags entries where alpha/beta was not reported by the source so the
UI can require the user to supply one before using it for EQD2 conversion.
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass
from typing import Optional

from core.paths import resource_path

BANK_PATH = resource_path("data", "lkb_parameter_bank.json")


@dataclass
class LKBBankEntry:
    organ: str
    endpoint: str
    label: str              # "Author et al. Year" -- what the picker shows
    n: float
    m: float
    td50_gy: float
    alpha_beta: Optional[float]   # None => not reported by the source
    vref: str
    dose_reference: str
    status: str              # historical | quantec_update | conditional | ...
    selectable: bool          # False = documentation-only, not directly usable
    source: str
    url: Optional[str]
    notes: str
    model_id: str = ""
    cohort_modality: str = ""

    @property
    def alpha_beta_missing(self) -> bool:
        return self.alpha_beta is None


_cache: list[LKBBankEntry] | None = None


def load_bank(path: str = BANK_PATH) -> list[LKBBankEntry]:
    global _cache
    if _cache is not None and path == BANK_PATH:
        return _cache
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"LKB parameter bank not found at:\n{path}\n\n"
            "If you're running the packaged .exe, this build is missing its "
            "bundled data files -- rebuild with build_exe.bat (which now "
            "includes --add-data \"data;data\")."
        )
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    entries = [LKBBankEntry(**r) for r in raw]
    if path == BANK_PATH:
        _cache = entries
    return entries


def get_organs(entries: list[LKBBankEntry] | None = None, selectable_only: bool = True) -> list[str]:
    entries = entries if entries is not None else load_bank()
    organs = {e.organ for e in entries if (e.selectable or not selectable_only)}
    return sorted(organs)


def get_endpoints(organ: str, entries: list[LKBBankEntry] | None = None,
                   selectable_only: bool = True) -> list[str]:
    entries = entries if entries is not None else load_bank()
    endpoints = {e.endpoint for e in entries
                 if e.organ == organ and (e.selectable or not selectable_only)}
    return sorted(endpoints)


def get_parameter_sets(organ: str, endpoint: str,
                        entries: list[LKBBankEntry] | None = None,
                        selectable_only: bool = True) -> list[LKBBankEntry]:
    entries = entries if entries is not None else load_bank()
    return [e for e in entries if e.organ == organ and e.endpoint == endpoint
            and (e.selectable or not selectable_only)]
