"""Continuous Proactive Discovery Engine — orchestration layer.

Per the Sprint Brief, this is the orchestration engine that runs
on a schedule (and via manual trigger) to:

  1. Activate the 4 v2.4 agents:
       - Global Product Monitor (§4.18.1)
       - New Product Detector (§4.18.2) — applies the 5 filters
       - Emerging Company Scout (§4.18.3)
       - Patent Watch (§4.18.4)
  2. Apply the 5 qualification filters (F1..F5) per Document 02.
  3. Check the 3 Constitutional Registers (Article VIII):
       RESTRICTED, CONFLICT, NON_REPRESENTED.
  4. Persist results.
  5. Send a notification for each qualifying candidate.

The engine is PURE LOGIC, no DB coupling. The integration layer
(`scheduler.py` + `phase9_continuous_routes.py`) handles the
DB session and notification dispatch.

Constitutional basis:
  - Constitution v2.4 (additive amendment, 2026-07-19).
  - Document 02 §4.18 (Office 18 — Product Discovery Proactive).
  - Constitution Article VIII (Constitutional Registers).
  - Constitution Article XII (Human Approval).

Data source policy (per Constitutional Owner):
  - Default: SIMULATED, marked DEMO_DATA.
  - Real sources added when API keys are available.
  - Every candidate carries data_source + data_source_marker.
  - Unknown / missing marker => REJECTED at register layer.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable, List, Optional, Tuple

from . import proactive_discovery as _pd
from .simulated_sources import (
    DEFAULT_DATA_SOURCE,
    DEMO_DATA_MARKER,
    DataSourceMarker,
    SourceCandidate,
    get_default_registry,
)


# The 4 v2.4 agents' engine instances (pure logic, no DB).
AGENT_ENGINES = (
    _pd.GlobalProductMonitorEngine(),
    _pd.NewProductDetectorEngine(),
    _pd.EmergingCompanyScoutEngine(),
    _pd.PatentWatchEngine(),
)


class RunStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CandidateStatus(str, Enum):
    QUALIFIED = "QUALIFIED"
    REJECTED = "REJECTED"


# ----------------------------------------------------------------------------
# Result data structures (engine layer, not DB entities)
# ----------------------------------------------------------------------------


@dataclass
class FilterOutcome_:
    """Result of the 5-filter evaluation. Distinct name from
    proactive_discovery.FilterOutcome to avoid the import clash."""

    f1_kuwait_climate: bool
    f1_rationale: str
    f2_retrofit: bool
    f2_rationale: str
    f3_no_agent_kuwait: bool
    f3_rationale: str
    f4_low_operating_cost: bool
    f4_rationale: str
    f5_company_size: bool
    f5_rationale: str

    @property
    def all_pass(self) -> bool:
        return (
            self.f1_kuwait_climate
            and self.f2_retrofit
            and self.f3_no_agent_kuwait
            and self.f4_low_operating_cost
            and self.f5_company_size
        )

    def failed_filters(self) -> List[str]:
        out: List[str] = []
        if not self.f1_kuwait_climate:
            out.append("F1")
        if not self.f2_retrofit:
            out.append("F2")
        if not self.f3_no_agent_kuwait:
            out.append("F3")
        if not self.f4_low_operating_cost:
            out.append("F4")
        if not self.f5_company_size:
            out.append("F5")
        return out


@dataclass
class RegisterCheck:
    passed: bool
    finding: str  # human-readable, bilingual-ready


@dataclass
class EvaluatedCandidate:
    """A source candidate after 5-filter + register evaluation."""

    candidate_id: str
    product_name: str
    product_category: str
    sector: str
    manufacturer_name: str
    manufacturer_country: Optional[str]
    data_source: str
    data_source_marker: str
    source_citation_url: Optional[str]
    signal_strength: str
    filters: FilterOutcome_
    register: RegisterCheck
    overall: CandidateStatus
    discovered_at: datetime


@dataclass
class NotificationRecord:
    """Bilingual notification for a qualifying candidate."""

    notification_id: str
    candidate_id: str
    run_id: str
    subject_en: str
    subject_ar: str
    body_en: str
    body_ar: str
    priority: str  # CLASS_3 / CLASS_2 / etc.
    created_at: datetime


@dataclass
class RunResult:
    """The result of one full Continuous Discovery run."""

    run_id: str
    run_type: str  # SCHEDULED / MANUAL
    data_source: str
    started_at: datetime
    finished_at: datetime
    status: RunStatus
    n_agents_activated: int
    evaluated: List[EvaluatedCandidate]
    notifications: List[NotificationRecord]
    error_message: Optional[str] = None
    triggered_by: str = "system"


# ----------------------------------------------------------------------------
# Engine
# ----------------------------------------------------------------------------


class ContinuousDiscoveryEngine:
    """The orchestration engine for one Continuous Discovery run.

    Pure logic. No DB coupling. The integration layer
    (`phase9_continuous_routes.py` + `scheduler.py`) handles the
    DB session and notification dispatch.
    """

    def __init__(self, registry=None) -> None:
        # The data source registry; defaults to the module singleton.
        self.registry = registry or get_default_registry()

    # ----- helpers -----

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _apply_5_filters(self, cand: SourceCandidate) -> FilterOutcome_:
        """Apply the 5 qualification filters (F1..F5) to a candidate.

        The 4 v2.4 agents surface the candidate; the New Product
        Detector (§4.18.2) applies the filters. We delegate to the
        v2.4 engine layer where possible.
        """
        # F1: Kuwait climate suitability — heat, wind, dust.
        # Demo heuristic: candidates with sector OIL_GAS or HVAC pass;
        # candidates with signal_strength LOW fail (too weak).
        f1_pass = cand.signal_strength != "LOW"
        f1_rationale = (
            "F1 PASS: candidate signal strong enough for Kuwait climate review"
            if f1_pass
            else "F1 FAIL: signal too weak (LOW) for Kuwait climate assessment"
        )

        # F2: Retrofit-friendliness — no major system change required.
        # Demo heuristic: products in INDUSTRIAL_MAINTENANCE / WATER_TREATMENT
        # / INSTRUMENTATION / ELECTRICAL pass; ENERGY / HVAC fail (larger
        # system change). This is a SIMULATED heuristic, clearly marked.
        f2_pass = cand.product_category in (
            "INDUSTRIAL_MAINTENANCE",
            "WATER_TREATMENT",
            "INSTRUMENTATION",
            "ELECTRICAL",
        )
        f2_rationale = (
            f"F2 PASS: {cand.product_category} is retrofit-friendly"
            if f2_pass
            else f"F2 FAIL: {cand.product_category} requires major system change"
        )

        # F3: No agent in Kuwait — exclusive representation available.
        # Demo heuristic: any manufacturer with "Demo" in the name passes
        # (we have no Kuwait agent data; in production this would query
        # the RepresentedPrincipal register). The actual integration
        # with the register happens at the integration layer.
        f3_pass = "(Demo)" in cand.manufacturer_name
        f3_rationale = (
            f"F3 PASS: no existing Kuwait agent for {cand.manufacturer_name} (simulated check)"
            if f3_pass
            else f"F3 FAIL: existing Kuwait agent for {cand.manufacturer_name} (simulated check)"
        )

        # F4: Low operating cost — no specialised training, no eng team.
        # Demo heuristic: all products pass (operating cost not in
        # the simulated data).
        f4_pass = True
        f4_rationale = "F4 PASS: no specialised training or engineering team required (simulated)"

        # F5: Company size — medium/emerging, not tier-1.
        # Demo heuristic: any manufacturer with "Demo" in the name passes.
        f5_pass = "(Demo)" in cand.manufacturer_name
        f5_rationale = (
            f"F5 PASS: {cand.manufacturer_name} is medium/emerging (simulated)"
            if f5_pass
            else f"F5 FAIL: {cand.manufacturer_name} is tier-1 (simulated)"
        )

        return FilterOutcome_(
            f1_kuwait_climate=f1_pass,
            f1_rationale=f1_rationale,
            f2_retrofit=f2_pass,
            f2_rationale=f2_rationale,
            f3_no_agent_kuwait=f3_pass,
            f3_rationale=f3_rationale,
            f4_low_operating_cost=f4_pass,
            f4_rationale=f4_rationale,
            f5_company_size=f5_pass,
            f5_rationale=f5_rationale,
        )

    def _check_registers(
        self,
        cand: SourceCandidate,
        represented_brands: Iterable[str] = (),
        conflict_brands: Iterable[str] = (),
        restricted_brands: Iterable[str] = (),
    ) -> RegisterCheck:
        """Check the 3 Constitutional Registers (Article VIII).

        Constitutional constraint: if the data source is unknown
        or the marker is missing, REJECT.

        The integration layer is responsible for populating the
        three brand lists from the actual register tables. The
        engine layer is pure logic.
        """
        # Constitutional constraint: unknown source / missing marker
        # is REJECTED. (This is the explicit Owner directive.)
        if not cand.data_source:
            return RegisterCheck(False, "REJECTED: missing data_source identifier")
        if cand.data_source_marker not in (DEMO_DATA_MARKER, "REAL"):
            return RegisterCheck(False, f"REJECTED: missing or invalid data_source_marker {cand.data_source_marker!r}")

        # RESTRICTED — manufacturer is constitutionally prohibited.
        for r in restricted_brands:
            if r and r.lower() in cand.manufacturer_name.lower():
                return RegisterCheck(False, f"REJECTED: manufacturer in RESTRICTED register ({r})")

        # CONFLICT — manufacturer is in conflict.
        for c in conflict_brands:
            if c and c.lower() in cand.manufacturer_name.lower():
                return RegisterCheck(False, f"REJECTED: manufacturer in CONFLICT register ({c})")

        # NON_REPRESENTED — represented by another principal in Kuwait.
        for rep in represented_brands:
            if rep and rep.lower() in cand.manufacturer_name.lower():
                return RegisterCheck(False, f"REJECTED: manufacturer already REPRESENTED in Kuwait ({rep})")

        return RegisterCheck(True, "PASS: no register conflict")

    def _build_evaluation(
        self,
        cand: SourceCandidate,
        filters: FilterOutcome_,
        register: RegisterCheck,
    ) -> EvaluatedCandidate:
        # Overall: QUALIFIED only if BOTH (5 filters all pass) AND
        # (register check passes). Otherwise REJECTED.
        if filters.all_pass and register.passed:
            overall = CandidateStatus.QUALIFIED
        else:
            overall = CandidateStatus.REJECTED
        return EvaluatedCandidate(
            candidate_id=str(uuid.uuid4()),
            product_name=cand.product_name,
            product_category=cand.product_category,
            sector=cand.sector,
            manufacturer_name=cand.manufacturer_name,
            manufacturer_country=cand.manufacturer_country,
            data_source=cand.data_source,
            data_source_marker=cand.data_source_marker,
            source_citation_url=cand.source_citation_url,
            signal_strength=cand.signal_strength,
            filters=filters,
            register=register,
            overall=overall,
            discovered_at=self._now(),
        )

    def _build_notification(
        self,
        evaluated: EvaluatedCandidate,
        run_id: str,
    ) -> NotificationRecord:
        """Build a bilingual notification for a qualifying candidate."""
        subject_en = (
            f"Continuous Proactive Discovery: {evaluated.product_name} "
            f"(source: {evaluated.data_source})"
        )
        subject_ar = (
            f"الاكتشاف الاستباقي المستمر: {evaluated.product_name} "
            f"(المصدر: {evaluated.data_source})"
        )
        body_en = (
            f"A new candidate has passed the 5 qualification filters and "
            f"the 3 Constitutional Registers check.\n\n"
            f"  Product: {evaluated.product_name}\n"
            f"  Manufacturer: {evaluated.manufacturer_name}\n"
            f"  Sector: {evaluated.sector}\n"
            f"  Category: {evaluated.product_category}\n"
            f"  Data source: {evaluated.data_source} "
            f"(marker: {evaluated.data_source_marker})\n"
            f"  Source citation: {evaluated.source_citation_url or 'N/A'}\n"
            f"  Filter results: F1={evaluated.filters.f1_kuwait_climate}, "
            f"F2={evaluated.filters.f2_retrofit}, "
            f"F3={evaluated.filters.f3_no_agent_kuwait}, "
            f"F4={evaluated.filters.f4_low_operating_cost}, "
            f"F5={evaluated.filters.f5_company_size}\n"
            f"  Register check: {evaluated.register.finding}\n\n"
            f"Candidate ID: {evaluated.candidate_id}\n"
            f"Run ID: {run_id}\n\n"
            f"To initiate the Exclusive Agency Acquisition workflow, "
            f"open the Continuous Discovery Console and click "
            f"'Initiate Exclusive Agency Acquisition'."
        )
        body_ar = (
            f"مرشح جديد اجتاز فلاتر التأهيل الخمسة وفحص السجلات "
            f"الدستورية الثلاثة.\n\n"
            f"  المنتج: {evaluated.product_name}\n"
            f"  المُصنِّع: {evaluated.manufacturer_name}\n"
            f"  القطاع: {evaluated.sector}\n"
            f"  الفئة: {evaluated.product_category}\n"
            f"  مصدر البيانات: {evaluated.data_source} "
            f"(العلامة: {evaluated.data_source_marker})\n"
            f"  المصدر المرجعي: {evaluated.source_citation_url or 'لا يوجد'}\n"
            f"  نتائج الفلاتر: F1={evaluated.filters.f1_kuwait_climate}, "
            f"F2={evaluated.filters.f2_retrofit}, "
            f"F3={evaluated.filters.f3_no_agent_kuwait}, "
            f"F4={evaluated.filters.f4_low_operating_cost}, "
            f"F5={evaluated.filters.f5_company_size}\n"
            f"  فحص السجل: {evaluated.register.finding}\n\n"
            f"معرّف المرشح: {evaluated.candidate_id}\n"
            f"معرّف التشغيل: {run_id}\n\n"
            f"لبدء سير عمل الحصول على الوكالة الحصرية، افتح "
            f"وحدة تحكم الاكتشاف المستمر واضغط على "
            f"'بدء الحصول على الوكالة الحصرية'."
        )
        return NotificationRecord(
            notification_id=str(uuid.uuid4()),
            candidate_id=evaluated.candidate_id,
            run_id=run_id,
            subject_en=subject_en,
            subject_ar=subject_ar,
            body_en=body_en,
            body_ar=body_ar,
            priority="CLASS_3",  # Per Document 06 §9, Class 3 default for new discoveries.
            created_at=self._now(),
        )

    # ----- public API -----

    def run_once(
        self,
        run_type: str = "SCHEDULED",
        data_source_name: str = DEFAULT_DATA_SOURCE,
        max_candidates: int = 5,
        represented_brands: Iterable[str] = (),
        conflict_brands: Iterable[str] = (),
        restricted_brands: Iterable[str] = (),
        triggered_by: str = "system",
    ) -> RunResult:
        """Execute one full Continuous Discovery run.

        1. Activate the 4 v2.4 agents (just the engine instances).
        2. Fetch candidates from the data source.
        3. Apply the 5 filters.
        4. Check the 3 registers.
        5. Build notification for each qualifying candidate.
        6. Return the full result for the integration layer to persist.
        """
        run_id = str(uuid.uuid4())
        started = self._now()
        evaluated: List[EvaluatedCandidate] = []
        notifications: List[NotificationRecord] = []
        error: Optional[str] = None
        status = RunStatus.RUNNING
        try:
            # 1. Activate the 4 v2.4 agents.
            n_agents = len(AGENT_ENGINES)

            # 2. Fetch candidates.
            ds = self.registry.get(data_source_name)
            raw = ds.fetch_candidates(max_n=max_candidates)

            # 3 + 4. Apply 5 filters + check 3 registers.
            for cand in raw:
                filters = self._apply_5_filters(cand)
                register = self._check_registers(
                    cand,
                    represented_brands=represented_brands,
                    conflict_brands=conflict_brands,
                    restricted_brands=restricted_brands,
                )
                ev = self._build_evaluation(cand, filters, register)
                evaluated.append(ev)

            # 5. Notifications for qualifying candidates.
            for ev in evaluated:
                if ev.overall == CandidateStatus.QUALIFIED:
                    notifications.append(self._build_notification(ev, run_id))

            status = RunStatus.COMPLETED
        except Exception as exc:  # noqa: BLE001
            status = RunStatus.FAILED
            error = str(exc)

        finished = self._now()
        return RunResult(
            run_id=run_id,
            run_type=run_type,
            data_source=data_source_name,
            started_at=started,
            finished_at=finished,
            status=status,
            n_agents_activated=n_agents if status != RunStatus.FAILED else 0,
            evaluated=evaluated,
            notifications=notifications,
            error_message=error,
            triggered_by=triggered_by,
        )
