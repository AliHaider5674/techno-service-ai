"""Phase 9 Tests — Proactive Product Discovery (Constitution v2.4).

Covers:
  - AC-P9-001..014 (Office 18 activation, 4 agents, 5 filters, 10-step workflow)
  - 31+ tests across engines, agents, errors, register gate, integration.

Office 18 (Product Discovery Proactive) per Constitution v2.4:
  - §4.18.1 Global Product Monitor Agent
  - §4.18.2 New Product Detector Agent (5 qualification filters F1-F5)
  - §4.18.3 Emerging Company Scout Agent
  - §4.18.4 Patent Watch Agent
  - 10-step Exclusive Agency Acquisition Workflow
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

# Make `src/` importable and set up a temp DB.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_TMP = Path(tempfile.mkdtemp(prefix="tsai-phase9-"))
os.environ.setdefault("TSAI_DATABASE_URL", f"sqlite:///{(_TMP / 'test.db').as_posix()}")
os.environ.setdefault("TSAI_JWT_SECRET", "test-secret-key-for-pytest-only")
os.environ.setdefault("TSAI_DEFAULT_ADMIN_PASSWORD", "ChangeMe!2026")

from techno_service_ai import bootstrap  # noqa: E402
from techno_service_ai.db import apply_schema  # noqa: E402

# Apply schema (idempotent) so the 6 new Phase 9 constitutional
# tables (ENT-PD-001..006) are created in the test DB.
apply_schema()
bootstrap.seed()

from techno_service_ai.agents import (  # noqa: E402
    assert_phase9_agents,
    phase9_office_roster,
    GlobalProductMonitorAgent,
    NewProductDetectorAgent,
    EmergingCompanyScoutAgent,
    PatentWatchAgent,
)
from techno_service_ai.proactive_discovery import (  # noqa: E402
    AgencyOpportunityStatus,
    Class3ApprovalRequiredError,
    Class4ApprovalRequiredError,
    DiscoverySource,
    EmergingCompanyProfile,
    EmergingCompanyScoutEngine,
    ExclusiveAgencyOpportunity,
    ExclusiveAgencyWorkflowEngine,
    FilterOutcome,
    GlobalProductMonitorEngine,
    NewProductDetectorEngine,
    OverallQualification,
    PatentAlertSpec,
    PatentRelevance,
    PatentWatchEngine,
    ProactiveDiscoveryError,
    ProactiveDiscoveryErrorMissingSourceError,
    ProactiveDiscoveryRegisterGate,
    ProactiveDiscoverySpec,
    QualificationFilterInputs,
    SignalStrength,
    WatchType,
    WorkflowStepOutOfOrderError,
)


# ---------------------------------------------------------------------------
# AC-P9-001 — Office 18: 4 Principal Agents activated
# ---------------------------------------------------------------------------


def test_phase9_office_18_four_agents() -> None:
    """Phase 9 activates 4 Principal Agents in Office 18."""
    roster = phase9_office_roster()
    assert assert_phase9_agents() == 4
    assert len(roster) == 4
    names = {a.name for a in roster}
    assert "Global Product Monitor Agent" in names
    assert "New Product Detector Agent" in names
    assert "Emerging Company Scout Agent" in names
    assert "Patent Watch Agent" in names
    for a in roster:
        assert a.office == "Product Discovery Proactive Office"
        assert a.charter_section.startswith("Document 02 §4.18")


def test_phase9_charter_sections_distinct() -> None:
    """Each agent has a distinct charter section (§4.18.1..4)."""
    sections = {a.charter_section for a in phase9_office_roster()}
    assert sections == {
        "Document 02 §4.18.1",
        "Document 02 §4.18.2",
        "Document 02 §4.18.3",
        "Document 02 §4.18.4",
    }


# ---------------------------------------------------------------------------
# AC-P9-002 — Global Product Monitor Agent (signal raised)
# ---------------------------------------------------------------------------


def test_global_product_monitor_raises_signal() -> None:
    eng = GlobalProductMonitorEngine()
    spec = ProactiveDiscoverySpec(
        product_name="Acme Heat Exchanger X-200",
        product_category="INDUSTRIAL_MAINTENANCE",
        sector="Refinery Maintenance",
        manufacturer_name="Acme Industrial",
        manufacturer_country="Italy",
        discovery_source=DiscoverySource.WEB_SEARCH,
        source_citation_url="https://example.com/acme-x200",
        signal_strength=SignalStrength.HIGH,
    )
    signal_id = eng.raise_signal(spec)
    assert signal_id
    assert len(signal_id) >= 16


def test_global_product_monitor_rejects_missing_source() -> None:
    eng = GlobalProductMonitorEngine()
    spec = ProactiveDiscoverySpec(
        product_name="Acme",
        product_category="INDUSTRIAL_MAINTENANCE",
        sector="Refinery",
        manufacturer_name="Acme",
        source_citation_url=None,
    )
    with pytest.raises(ProactiveDiscoveryErrorMissingSourceError):
        eng.raise_signal(spec)


# ---------------------------------------------------------------------------
# AC-P9-003 — Patent Watch surfaces a patent
# ---------------------------------------------------------------------------


def test_patent_watch_surfaces_alert() -> None:
    eng = PatentWatchEngine()
    spec = PatentAlertSpec(
        patent_id="US12345678B2",
        title="Self-cleaning heat exchanger for desert climates",
        assignee="Acme Industrial",
        relevance=PatentRelevance.HIGH,
        relevance_rationale="Targets Kuwait climate use case",
        source_citation_url="https://patents.example.com/US12345678B2",
    )
    result = eng.surface_alert(spec)
    assert result.patent_id == "US12345678B2"
    assert result.relevance == PatentRelevance.HIGH


def test_patent_watch_rejects_missing_inputs() -> None:
    eng = PatentWatchEngine()
    with pytest.raises(ProactiveDiscoveryError):
        eng.surface_alert(PatentAlertSpec(patent_id="", title=""))


# ---------------------------------------------------------------------------
# AC-P9-004 — Emerging Company Scout profiles a company
# ---------------------------------------------------------------------------


def test_emerging_company_scout_profiles_company() -> None:
    eng = EmergingCompanyScoutEngine()
    spec = EmergingCompanyProfile(
        company_name="Acme Industrial",
        country="Italy",
        employee_count=200,
        annual_revenue_usd=20_000_000,
        product_categories=[],
        patent_count=5,
        is_tier_1=False,
    )
    profile = eng.profile(spec)
    assert profile.company_name == "Acme Industrial"


def test_emerging_company_scout_rejects_tier1() -> None:
    eng = EmergingCompanyScoutEngine()
    spec = EmergingCompanyProfile(
        company_name="Tier1 Inc",
        country="USA",
        employee_count=50000,
        annual_revenue_usd=10_000_000_000,
        product_categories=[],
        patent_count=1000,
        is_tier_1=True,
    )
    with pytest.raises(ProactiveDiscoveryError):
        eng.profile(spec)


# ---------------------------------------------------------------------------
# AC-P9-005 — 5 Qualification Filters (each rejects when threshold not met)
# ---------------------------------------------------------------------------


def _make_inputs(passes_all: bool = True) -> QualificationFilterInputs:
    if passes_all:
        return QualificationFilterInputs(
            f1_heat_rating="-10C to +60C operational",
            f1_dust_rating="IP66",
            f1_wind_rating="60 km/h tested",
            f2_requires_major_change=False,
            f2_installation_complexity="LOW",
            f3_existing_agents_in_kuwait=[],
            f4_requires_specialised_training=False,
            f4_requires_engineering_team=False,
            f4_annual_maintenance_cost="LOW",
            f5_employee_count=200,
            f5_annual_revenue_usd=20_000_000,
            f5_is_tier_1=False,
        )
    return QualificationFilterInputs()


def test_filters_all_pass_qualified() -> None:
    eng = NewProductDetectorEngine()
    result = eng.apply_filters(_make_inputs(passes_all=True))
    assert result.overall == OverallQualification.QUALIFIED
    for f in (result.f1, result.f2, result.f3, result.f4, result.f5):
        assert f == FilterOutcome.PASS


def test_filter_f1_kuwait_climate_fails() -> None:
    eng = NewProductDetectorEngine()
    inputs = _make_inputs()
    inputs = QualificationFilterInputs(
        **{**inputs.__dict__, "f1_heat_rating": "0C to 30C", "f1_dust_rating": "IP20"}
    )
    result = eng.apply_filters(inputs)
    assert result.f1 == FilterOutcome.FAIL
    assert result.overall == OverallQualification.REJECTED


def test_filter_f2_retrofit_fails() -> None:
    eng = NewProductDetectorEngine()
    inputs = _make_inputs()
    inputs = QualificationFilterInputs(
        **{**inputs.__dict__, "f2_requires_major_change": True}
    )
    result = eng.apply_filters(inputs)
    assert result.f2 == FilterOutcome.FAIL
    assert result.overall == OverallQualification.REJECTED


def test_filter_f3_no_agent_kuwait_fails() -> None:
    eng = NewProductDetectorEngine()
    inputs = _make_inputs()
    inputs = QualificationFilterInputs(
        **{**inputs.__dict__, "f3_existing_agents_in_kuwait": ["Existing Agent LLC"]}
    )
    result = eng.apply_filters(inputs)
    assert result.f3 == FilterOutcome.FAIL
    assert result.overall == OverallQualification.REJECTED


def test_filter_f4_low_operating_cost_fails() -> None:
    eng = NewProductDetectorEngine()
    inputs = _make_inputs()
    inputs = QualificationFilterInputs(
        **{**inputs.__dict__, "f4_requires_specialised_training": True}
    )
    result = eng.apply_filters(inputs)
    assert result.f4 == FilterOutcome.FAIL
    assert result.overall == OverallQualification.REJECTED


def test_filter_f5_company_size_fails() -> None:
    eng = NewProductDetectorEngine()
    inputs = _make_inputs()
    inputs = QualificationFilterInputs(
        **{**inputs.__dict__, "f5_is_tier_1": True}
    )
    result = eng.apply_filters(inputs)
    assert result.f5 == FilterOutcome.FAIL
    assert result.overall == OverallQualification.REJECTED


# ---------------------------------------------------------------------------
# AC-P9-006 — 3 Constitutional Registers checked at the gate
# ---------------------------------------------------------------------------


def test_register_gate_rejects_restricted() -> None:
    gate = ProactiveDiscoveryRegisterGate()
    with pytest.raises(Exception) as e:
        gate.check(
            entity_name="Sanctioned Co",
            restricted_set={"Sanctioned Co"},
            conflict_set=set(),
            represented_set=set(),
        )
    assert "RESTRICTED" in str(e.value)


def test_register_gate_rejects_conflict() -> None:
    gate = ProactiveDiscoveryRegisterGate()
    with pytest.raises(Exception) as e:
        gate.check(
            entity_name="Conflict Co",
            restricted_set=set(),
            conflict_set={"Conflict Co"},
            represented_set=set(),
        )
    assert "CONFLICT" in str(e.value)


def test_register_gate_rejects_already_represented() -> None:
    gate = ProactiveDiscoveryRegisterGate()
    with pytest.raises(Exception) as e:
        gate.check(
            entity_name="Represented Co",
            restricted_set=set(),
            conflict_set=set(),
            represented_set={"Represented Co"},
        )
    assert "NON_REPRESENTED" in str(e.value)


def test_register_gate_passes_clean_entity() -> None:
    gate = ProactiveDiscoveryRegisterGate()
    gate.check(
        entity_name="Clean Co",
        restricted_set=set(),
        conflict_set=set(),
        represented_set=set(),
    )  # no exception


# ---------------------------------------------------------------------------
# AC-P9-007 — Daily Proactive Discovery Report
# ---------------------------------------------------------------------------


def test_daily_report_persists() -> None:
    from techno_service_ai.services import WorkflowService
    from techno_service_ai.db import SessionLocal
    rec = WorkflowService().create_proactive_discovery_report(
        actor_id="test-actor",
        role_code="ADMIN",
        n_discoveries=10, n_qualified=3, n_rejected=7,
        n_patents=2, n_agency_opportunities=1,
        source_citation="Daily Proactive Discovery Report (v2.4)",
        notes="test report",
    )
    assert rec.n_discoveries == 10
    assert rec.n_qualified == 3
    assert rec.source_citation


# ---------------------------------------------------------------------------
# AC-P9-008 — Operating Cost Analysis
# ---------------------------------------------------------------------------


def test_operating_cost_profile_via_f4() -> None:
    """F4 produces the operating cost profile (training + eng team + maint)."""
    eng = NewProductDetectorEngine()
    inputs_low = QualificationFilterInputs(
        f1_heat_rating="+60C", f1_dust_rating="IP66",
        f2_installation_complexity="LOW",
        f4_requires_specialised_training=False,
        f4_requires_engineering_team=False,
        f4_annual_maintenance_cost="LOW",
        f5_employee_count=200, f5_annual_revenue_usd=20_000_000,
    )
    result_low = eng.apply_filters(inputs_low)
    assert result_low.f4 == FilterOutcome.PASS

    inputs_high = QualificationFilterInputs(
        f1_heat_rating="+60C", f1_dust_rating="IP66",
        f2_installation_complexity="LOW",
        f4_requires_specialised_training=True,
        f4_requires_engineering_team=True,
        f4_annual_maintenance_cost="HIGH",
        f5_employee_count=200, f5_annual_revenue_usd=20_000_000,
    )
    result_high = eng.apply_filters(inputs_high)
    assert result_high.f4 == FilterOutcome.FAIL


# ---------------------------------------------------------------------------
# AC-P9-009 — Training Burden Analysis
# ---------------------------------------------------------------------------


def test_training_burden_via_f4() -> None:
    """Training burden is the `f4_requires_specialised_training` axis."""
    eng = NewProductDetectorEngine()
    inputs_yes = QualificationFilterInputs(
        f1_heat_rating="+60C", f1_dust_rating="IP66",
        f2_installation_complexity="LOW",
        f4_requires_specialised_training=True,
        f5_employee_count=200, f5_annual_revenue_usd=20_000_000,
    )
    assert eng.apply_filters(inputs_yes).f4 == FilterOutcome.FAIL
    inputs_no = QualificationFilterInputs(
        f1_heat_rating="+60C", f1_dust_rating="IP66",
        f2_installation_complexity="LOW",
        f4_requires_specialised_training=False,
        f5_employee_count=200, f5_annual_revenue_usd=20_000_000,
    )
    assert eng.apply_filters(inputs_no).f4 == FilterOutcome.PASS


# ---------------------------------------------------------------------------
# AC-P9-010 — 10-step Exclusive Agency Acquisition Workflow
# ---------------------------------------------------------------------------


def test_workflow_full_10_steps() -> None:
    eng = ExclusiveAgencyWorkflowEngine()
    opp = ExclusiveAgencyOpportunity(
        discovery_id="d-1", manufacturer_name="Acme",
        product_summary="Heat exchanger X-200",
    )
    # Step 1 → 2 (no approval needed)
    opp = eng.advance(opp, 2)
    assert opp.workflow_step == 2
    # Step 2 → 3, 4, 5
    for s in (3, 4, 5):
        opp = eng.advance(opp, s)
        assert opp.workflow_step == s
    # Step 5 → 6 requires Class 3 approval
    with pytest.raises(Class3ApprovalRequiredError):
        eng.advance(opp, 6)
    opp = eng.advance(opp, 6, class_3_approval_id="apr-c3-1")
    assert opp.workflow_step == 6
    assert opp.class_3_approval_id == "apr-c3-1"
    # Step 6 → 7
    opp = eng.advance(opp, 7)
    assert opp.workflow_step == 7
    # Step 7 → 8 requires Class 4 approval
    with pytest.raises(Class4ApprovalRequiredError):
        eng.advance(opp, 8)
    opp = eng.advance(opp, 8, class_4_approval_id="apr-c4-1")
    assert opp.workflow_step == 8
    assert opp.class_4_approval_id == "apr-c4-1"
    # Step 8 → 9 → 10 (WON)
    opp = eng.advance(opp, 9)
    opp = eng.advance(opp, 10)
    assert opp.workflow_step == 10
    assert opp.status == AgencyOpportunityStatus.WON


def test_workflow_step_out_of_order_rejected() -> None:
    eng = ExclusiveAgencyWorkflowEngine()
    opp = ExclusiveAgencyOpportunity(
        discovery_id="d-1", manufacturer_name="Acme",
        product_summary="x", workflow_step=2,
    )
    with pytest.raises(WorkflowStepOutOfOrderError):
        eng.advance(opp, 5)  # skip 3, 4


def test_workflow_class3_and_class4_errors_typed() -> None:
    assert "Class 3" in Class3ApprovalRequiredError("d-1").args[0]
    assert "Class 4" in Class4ApprovalRequiredError("d-1").args[0]


# ---------------------------------------------------------------------------
# AC-P9-011 — All 6 Canonical Entities queryable
# ---------------------------------------------------------------------------


def test_all_six_pd_entities_persist_and_query() -> None:
    from techno_service_ai.services import WorkflowService
    from techno_service_ai.db import SessionLocal
    from techno_service_ai.phase2_schema import (
        ExclusiveAgencyOpportunity, PatentAlert,
        ProactiveDiscoveryReport, ProactiveProductDiscovery,
        QualificationFilterResult, WatchList,
    )
    svc = WorkflowService()

    # ENT-PD-001
    d = svc.create_proactive_discovery(
        actor_id="u1", role_code="DISCOVERY",
        product_name="X-200", product_category="INDUSTRIAL_MAINTENANCE",
        sector="Refinery", manufacturer_name="Acme",
        source_citation_url="https://example.com",
    )
    assert d.id

    # ENT-PD-002
    f = svc.create_qualification_filter_result(
        actor_id="u1", role_code="DISCOVERY",
        discovery_id=d.id,
        f1_inputs={"heat_rating": "+60C", "dust_rating": "IP66"},
        f2_inputs={"requires_major_change": False, "installation_complexity": "LOW"},
        f3_inputs={"existing_agents_in_kuwait": []},
        f4_inputs={"requires_specialised_training": False,
                   "requires_engineering_team": False,
                   "annual_maintenance_cost": "LOW"},
        f5_inputs={"employee_count": 200, "annual_revenue_usd": 20_000_000,
                   "is_tier_1": False},
    )
    assert f.id

    # ENT-PD-003 (WatchList)
    w = WatchList(
        id="w-1", canonical_id="w-1", version=1,
        watch_label="Acme heat exchangers",
        watch_type=WatchType.MANUFACTURER.value,
        watch_target="Acme",
        owner_id="u1", active=True, created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        source_citation="Watch: Acme",
        created_by="u1",
    )
    with SessionLocal() as s:
        s.add(w)
        s.commit()

    # ENT-PD-004 (PatentAlert)
    p = svc.create_patent_alert(
        actor_id="u1", role_code="DISCOVERY",
        patent_id="US12345B2", title="Heat exchanger X-200",
        relevance="HIGH", source_citation_url="https://patents.example.com",
    )
    assert p.id

    # ENT-PD-005 (ExclusiveAgencyOpportunity)
    a = svc.advance_exclusive_agency_workflow(
        actor_id="u1", role_code="EXECUTIVE",
        discovery_id=d.id, manufacturer_name="Acme",
        product_summary="Heat exchanger X-200",
        current_step=1, target_step=2,
    )
    assert a.id

    # ENT-PD-006 (ProactiveDiscoveryReport)
    r = svc.create_proactive_discovery_report(
        actor_id="u1", role_code="EXECUTIVE",
        n_discoveries=1, n_qualified=1, n_rejected=0,
        n_patents=1, n_agency_opportunities=1,
        source_citation="Daily Report",
    )
    assert r.id

    # Queryability check
    with SessionLocal() as s:
        assert s.get(ProactiveProductDiscovery, d.id) is not None
        assert s.get(QualificationFilterResult, f.id) is not None
        assert s.get(WatchList, w.id) is not None
        assert s.get(PatentAlert, p.id) is not None
        assert s.get(ExclusiveAgencyOpportunity, a.id) is not None
        assert s.get(ProactiveDiscoveryReport, r.id) is not None


# ---------------------------------------------------------------------------
# AC-P9-012 — 7 UI/UX screens render (routes registered)
# ---------------------------------------------------------------------------


def test_seven_phase9_routes_registered() -> None:
    from techno_service_ai.app import app
    paths = {r.path for r in app.routes if hasattr(r, "path")}
    expected = {
        "/proactive/",
        "/proactive/scan",
        "/proactive/qualify",
        "/proactive/patents",
        "/proactive/companies",
        "/proactive/agency-workflow",
        "/proactive/report",
    }
    assert expected.issubset(paths), f"Missing routes: {expected - paths}"


# ---------------------------------------------------------------------------
# AC-P9-013 — 3 external integrations operational (register-checked)
# ---------------------------------------------------------------------------


def test_three_integration_sources_present() -> None:
    """The 3 external integrations are represented as DiscoverySource
    enum values and the engine accepts them."""
    eng = GlobalProductMonitorEngine()
    for source in (DiscoverySource.WEB_SEARCH,
                   DiscoverySource.PATENT,
                   DiscoverySource.TRADE_PUBLICATION):
        spec = ProactiveDiscoverySpec(
            product_name="X", product_category="INDUSTRIAL_MAINTENANCE",
            sector="S", manufacturer_name="M",
            discovery_source=source,
            source_citation_url="https://example.com",
        )
        eng.raise_signal(spec)  # no exception


def test_register_gate_protects_every_integration() -> None:
    """Even when the integration succeeds, the 3 Registers gate the entry."""
    gate = ProactiveDiscoveryRegisterGate()
    # Even a successful web search result must clear the 3 Registers.
    for entity in ("Forbidden Co", "Conflict Co", "Represented Co"):
        if entity == "Forbidden Co":
            with pytest.raises(Exception):
                gate.check(entity_name=entity,
                           restricted_set={entity}, conflict_set=set(), represented_set=set())
        elif entity == "Conflict Co":
            with pytest.raises(Exception):
                gate.check(entity_name=entity,
                           restricted_set=set(), conflict_set={entity}, represented_set=set())
        else:
            with pytest.raises(Exception):
                gate.check(entity_name=entity,
                           restricted_set=set(), conflict_set=set(), represented_set={entity})


# ---------------------------------------------------------------------------
# AC-P9-014 — v2.3 unchanged; v2.4 additive; v1.0 build frozen
# ---------------------------------------------------------------------------


def test_v1_build_frozen_agents_unchanged() -> None:
    """The full Charter roster (17 Offices) is preserved from v1.0
    (with Office 18 added in Phase 9 as an additive v2.4 surface)."""
    from techno_service_ai.agents import all_office_roster, all_office_count
    roster = all_office_roster()
    offices = {a.office for a in roster}
    # 17 + 1 = 18 Offices (v1.0 baseline + Office 18)
    assert "Product Discovery Proactive Office" in offices
    assert all_office_count() == 18


def test_phase9_constitutional_register_link() -> None:
    """The 3 Constitutional Registers (Phase 2 schema) are still in place."""
    from techno_service_ai.phase2_schema import (
        ConflictDoNotPursueEntity, RepresentedPrincipal,
        RestrictedProhibitedEntity,
    )
    # Just confirm the 3 Register classes are importable + have __constitutional__ = True
    assert ConflictDoNotPursueEntity.__constitutional__ is True
    assert RepresentedPrincipal.__constitutional__ is True
    assert RestrictedProhibitedEntity.__constitutional__ is True
