"""
ui/app_state.py

Central, shared application state for the BioSuitePy desktop app -- every
tab reads/writes this instead of passing data around directly, mirroring
how the original BioSuite keeps one "Current treatment plan" active
across all tabs.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal

from core.dvh import DVH
from core.ntcp_models import NTCPEndpoint
from core.tcp_models import TCPParams, LQSLRExtra


@dataclass
class TreatmentPlan:
    plan_id: str
    fractions: int
    prescription_dose_cgy: float
    fractions_per_day: int = 1
    fractions_per_week: int = 5
    fraction_delivery_min: float = 2.0
    # structure_name -> DVH, populated via the DVH import tab
    dvhs: dict = field(default_factory=dict)
    # structure_name -> associated endpoint name (from Model/Endpoint tab)
    dvh_associations: dict = field(default_factory=dict)

    @property
    def length_days(self) -> float:
        return (self.fractions / max(self.fractions_per_week, 1)) * 7.0


@dataclass
class EndpointDefinition:
    name: str                 # e.g. "Lung (pneumonitis)", "Rectum (bleeding)", "Prostate (TCP)"
    kind: str                  # "NTCP" or "TCP"
    model: str                  # "LKB" | "RS" | "SMD" | "EUD" for NTCP; "Marsden" | "LQ-SLR" for TCP
    ntcp_endpoint: Optional[NTCPEndpoint] = None
    tcp_params: Optional[TCPParams] = None
    gtv_volume_cm3: Optional[float] = None  # only used for TCP endpoints
    lq_slr_extra: Optional[LQSLRExtra] = None  # only used when model == "LQ-SLR"; see
    # ui/tcp_ntcp_compute.py -- previously collected in the Add-endpoint dialog
    # but never actually stored/used anywhere, so every LQ-SLR endpoint
    # silently computed as plain Marsden regardless of these parameters.


class AppState(QObject):
    """Holds all treatment plans + endpoint definitions for the session.
    Emits signals so tabs can refresh themselves when the shared state
    changes elsewhere."""

    plans_changed = pyqtSignal()
    endpoints_changed = pyqtSignal()
    active_plan_changed = pyqtSignal(str)
    dvh_data_changed = pyqtSignal()   # DVHs loaded/removed/associated -- other tabs must refresh

    def __init__(self):
        super().__init__()
        self.plans: dict[str, TreatmentPlan] = {}
        self.endpoints: dict[str, EndpointDefinition] = {}
        self.active_plan_id: Optional[str] = None

    # ------------------------------------------------------------------ #
    def add_plan(self, plan: TreatmentPlan):
        self.plans[plan.plan_id] = plan
        if self.active_plan_id is None:
            self.active_plan_id = plan.plan_id
        self.plans_changed.emit()

    def delete_plan(self, plan_id: str):
        self.plans.pop(plan_id, None)
        if self.active_plan_id == plan_id:
            self.active_plan_id = next(iter(self.plans), None)
        self.plans_changed.emit()

    def active_plan(self) -> Optional[TreatmentPlan]:
        return self.plans.get(self.active_plan_id) if self.active_plan_id else None

    def set_active_plan(self, plan_id: str):
        if plan_id in self.plans:
            self.active_plan_id = plan_id
            self.active_plan_changed.emit(plan_id)

    # ------------------------------------------------------------------ #
    def add_endpoint(self, ep: EndpointDefinition):
        self.endpoints[ep.name] = ep
        self.endpoints_changed.emit()

    def delete_endpoint(self, name: str):
        self.endpoints.pop(name, None)
        self.endpoints_changed.emit()
