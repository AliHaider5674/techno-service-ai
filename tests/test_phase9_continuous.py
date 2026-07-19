"""Phase 9 Continuous Proactive Discovery Tests.

Covers:
  - Scheduler lifecycle (start / pause / resume / stop).
  - Manual trigger.
  - 5-filter evaluation.
  - 3-register check (REJECT for missing marker, REJECT for
    RESTRICTED / CONFLICT / REPRESENTED).
  - Simulated data source (DEMO_DATA marker).
  - Bilingual notification (EN + AR).
  - Console route + bilingual rendering.
  - Notification integration: notification appears in the DB.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Make `src/` importable and set up a temp DB.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_TMP = Path(tempfile.mkdtemp(prefix="tsai-continuous-"))
os.environ.setdefault("TSAI_DATABASE_URL", f"sqlite:///{(_TMP / 'test.db').as_posix()}")
os.environ.setdefault("TSAI_JWT_SECRET", "test-secret-key-for-pytest-only")
os.environ.setdefault("TSAI_DEFAULT_ADMIN_PASSWORD", "ChangeMe!2026")

from techno_service_ai import bootstrap  # noqa: E402
from techno_service_ai.db import apply_schema  # noqa: E402

apply_schema()
bootstrap.seed()

from techno_service_ai import continuous_discovery as _cd  # noqa: E402
from techno_service_ai import simulated_sources as _ss  # noqa: E402
from techno_service_ai import scheduler as _sched_mod  # noqa: E402
from techno_service_ai.continuous_discovery import (  # noqa: E402
    CandidateStatus,
    ContinuousDiscoveryEngine,
    RunStatus,
)
from techno_service_ai.phase2_schema import (  # noqa: E402
    ConflictDoNotPursueEntity,
    ContinuousDiscoveryCandidate,
    ContinuousDiscoveryNotification,
    ContinuousSearchRun,
    RepresentedPrincipal,
    RestrictedProhibitedEntity,
    SchedulerState,
)
from techno_service_ai.scheduler import InProcessScheduler, _ensure_scheduler_state  # noqa: E402
from techno_service_ai.scheduler import _load_register_brands, _persist_run, _persist_candidates  # noqa: E402
from techno_service_ai.scheduler import _persist_notifications  # noqa: E402
from techno_service_ai.simulated_sources import (  # noqa: E402
    DEFAULT_DATA_SOURCE,
    DEMO_DATA_MARKER,
    DataSource,
    DataSourceRegistry,
    KNOWN_REAL_SOURCES,
    SimulatedDataSource,
    SourceCandidate,
    get_default_data_source,
    get_default_registry,
)


# ===========================================================================
# Simulated data source
# ===========================================================================


class TestSimulatedDataSource:
    def test_default_marker_is_demo_data(self) -> None:
        ds = SimulatedDataSource()
        assert ds.marker == DEMO_DATA_MARKER
        assert ds.name == DEFAULT_DATA_SOURCE

    def test_fetch_returns_n_candidates(self) -> None:
        ds = SimulatedDataSource(seed=42)
        out = ds.fetch_candidates(max_n=3)
        assert len(out) == 3
        for c in out:
            assert isinstance(c, SourceCandidate)
            assert c.data_source == "SIMULATED"
            assert c.data_source_marker == "DEMO_DATA"
            assert "(Demo)" in c.manufacturer_name  # Fictional marker.

    def test_deterministic_with_seed(self) -> None:
        a = SimulatedDataSource(seed=7).fetch_candidates(max_n=4)
        b = SimulatedDataSource(seed=7).fetch_candidates(max_n=4)
        names_a = [c.product_name for c in a]
        names_b = [c.product_name for c in b]
        assert names_a == names_b

    def test_registry_default(self) -> None:
        reg = get_default_registry()
        assert DEFAULT_DATA_SOURCE in reg.available()
        ds = reg.get(DEFAULT_DATA_SOURCE)
        assert isinstance(ds, SimulatedDataSource)

    def test_registry_rejects_unknown_source(self) -> None:
        class BadSource(DataSource):
            name = "FAKE_SOURCE"
            marker = "DEMO_DATA"
            def fetch_candidates(self, max_n: int = 5):
                return []
        with pytest.raises(ValueError, match="Unknown data source"):
            DataSourceRegistry().register(BadSource())

    def test_registry_rejects_bad_marker(self) -> None:
        class BadSource(DataSource):
            name = "SIMULATED"
            marker = "FAKE"
            def fetch_candidates(self, max_n: int = 5):
                return []
        with pytest.raises(ValueError, match="DEMO_DATA or REAL"):
            DataSourceRegistry().register(BadSource())

    def test_known_real_sources_frozen(self) -> None:
        assert "USPTO" in KNOWN_REAL_SOURCES
        assert "OPEN_CORPORATES" in KNOWN_REAL_SOURCES


# ===========================================================================
# 5-filter engine
# ===========================================================================


class TestFiveFilters:
    def setup_method(self) -> None:
        self.engine = ContinuousDiscoveryEngine()

    def test_industrial_maintenance_oil_gas_passes_demo(self) -> None:
        cand = SourceCandidate(
            product_name="Acme Pump (Demo)",
            product_category="INDUSTRIAL_MAINTENANCE",
            sector="OIL_GAS",
            manufacturer_name="Acme Pump Works (Demo)",
            manufacturer_country="Italy",
            signal_strength="HIGH",
            data_source="SIMULATED",
            data_source_marker="DEMO_DATA",
        )
        f = self.engine._apply_5_filters(cand)
        assert f.f1_kuwait_climate is True
        assert f.f2_retrofit is True
        assert f.f3_no_agent_kuwait is True
        assert f.f4_low_operating_cost is True
        assert f.f5_company_size is True
        assert f.all_pass is True

    def test_low_signal_strength_fails_f1(self) -> None:
        cand = SourceCandidate(
            product_name="Weak Signal (Demo)",
            product_category="INDUSTRIAL_MAINTENANCE",
            sector="OIL_GAS",
            manufacturer_name="Foo (Demo)",
            signal_strength="LOW",
            data_source="SIMULATED",
            data_source_marker="DEMO_DATA",
        )
        f = self.engine._apply_5_filters(cand)
        assert f.f1_kuwait_climate is False
        assert "F1 FAIL" in f.f1_rationale

    def test_hvac_fails_f2(self) -> None:
        cand = SourceCandidate(
            product_name="HVAC (Demo)",
            product_category="HVAC",
            sector="OIL_GAS",
            manufacturer_name="Foo (Demo)",
            signal_strength="HIGH",
            data_source="SIMULATED",
            data_source_marker="DEMO_DATA",
        )
        f = self.engine._apply_5_filters(cand)
        assert f.f2_retrofit is False
        assert "F2 FAIL" in f.f2_rationale

    def test_no_demo_marker_fails_f3(self) -> None:
        cand = SourceCandidate(
            product_name="No Marker (Demo)",
            product_category="INDUSTRIAL_MAINTENANCE",
            sector="OIL_GAS",
            manufacturer_name="No Marker Real Co.",  # no "(Demo)"
            signal_strength="HIGH",
            data_source="SIMULATED",
            data_source_marker="DEMO_DATA",
        )
        f = self.engine._apply_5_filters(cand)
        assert f.f3_no_agent_kuwait is False
        assert "F3 FAIL" in f.f3_rationale

    def test_failed_filters_helper(self) -> None:
        cand = SourceCandidate(
            product_name="Multi (Demo)",
            product_category="HVAC",  # fails F2
            sector="OIL_GAS",
            manufacturer_name="Foo (Demo)",
            signal_strength="LOW",  # fails F1
            data_source="SIMULATED",
            data_source_marker="DEMO_DATA",
        )
        f = self.engine._apply_5_filters(cand)
        assert "F1" in f.failed_filters()
        assert "F2" in f.failed_filters()


# ===========================================================================
# Register check
# ===========================================================================


class TestRegisterCheck:
    def setup_method(self) -> None:
        self.engine = ContinuousDiscoveryEngine()

    def _cand(self, name: str = "Acme (Demo)", marker: str = "DEMO_DATA", source: str = "SIMULATED") -> SourceCandidate:
        return SourceCandidate(
            product_name=name,
            product_category="INDUSTRIAL_MAINTENANCE",
            sector="OIL_GAS",
            manufacturer_name=name,
            signal_strength="HIGH",
            data_source=source,
            data_source_marker=marker,
        )

    def test_missing_data_source_rejected(self) -> None:
        c = self._cand()
        c.data_source = ""
        r = self.engine._check_registers(c)
        assert r.passed is False
        assert "missing data_source" in r.finding

    def test_missing_marker_rejected(self) -> None:
        c = self._cand()
        c.data_source_marker = "FAKE"
        r = self.engine._check_registers(c)
        assert r.passed is False
        assert "missing or invalid" in r.finding

    def test_restricted_register_rejects(self) -> None:
        c = self._cand(name="Evil Co. (Demo)")
        r = self.engine._check_registers(c, restricted_brands=["Evil Co."])
        assert r.passed is False
        assert "RESTRICTED" in r.finding

    def test_conflict_register_rejects(self) -> None:
        c = self._cand(name="Hostile Co. (Demo)")
        r = self.engine._check_registers(c, conflict_brands=["Hostile Co."])
        assert r.passed is False
        assert "CONFLICT" in r.finding

    def test_represented_register_rejects(self) -> None:
        c = self._cand(name="AlreadyRepped Co. (Demo)")
        r = self.engine._check_registers(c, represented_brands=["AlreadyRepped Co."])
        assert r.passed is False
        assert "REPRESENTED" in r.finding

    def test_clean_candidate_passes(self) -> None:
        c = self._cand(name="Fresh Co. (Demo)")
        r = self.engine._check_registers(c)
        assert r.passed is True
        assert "no register conflict" in r.finding


# ===========================================================================
# Run once
# ===========================================================================


class TestRunOnce:
    def setup_method(self) -> None:
        self.engine = ContinuousDiscoveryEngine(
            registry=DataSourceRegistry()  # fresh registry
        )
        # Register a fresh SimulatedDataSource with a fixed seed.
        self.engine.registry.register(SimulatedDataSource(seed=1))

    def test_run_activates_4_agents(self) -> None:
        result = self.engine.run_once(
            run_type="MANUAL",
            data_source_name="SIMULATED",
            max_candidates=5,
        )
        assert result.status == RunStatus.COMPLETED
        assert result.n_agents_activated == 4

    def test_run_surfaces_candidates(self) -> None:
        result = self.engine.run_once(
            run_type="MANUAL",
            data_source_name="SIMULATED",
            max_candidates=3,
        )
        assert len(result.evaluated) == 3
        for c in result.evaluated:
            assert c.data_source == "SIMULATED"
            assert c.data_source_marker == "DEMO_DATA"

    def test_run_creates_notifications_for_qualified(self) -> None:
        result = self.engine.run_once(
            run_type="MANUAL",
            data_source_name="SIMULATED",
            max_candidates=5,
        )
        n_qualified = sum(1 for c in result.evaluated if c.overall == CandidateStatus.QUALIFIED)
        assert len(result.notifications) == n_qualified
        # Each notification is bilingual.
        for n in result.notifications:
            assert n.subject_en
            assert n.subject_ar
            assert n.body_en
            assert n.body_ar
            assert n.priority == "CLASS_3"
            assert "مرشح جديد" in n.body_ar  # Arabic for "A new candidate"
            assert "A new candidate" in n.body_en

    def test_run_failure_returns_failed(self) -> None:
        # Use a non-existent data source name.
        result = self.engine.run_once(
            run_type="MANUAL",
            data_source_name="BOGUS",
            max_candidates=3,
        )
        assert result.status == RunStatus.FAILED
        assert result.error_message is not None


# ===========================================================================
# Persistence helpers
# ===========================================================================


class TestPersistence:
    def test_ensure_scheduler_state_creates_singleton(self) -> None:
        from techno_service_ai.db import session_scope
        with session_scope() as s:
            # delete any existing state
            for row in s.execute(__import__("sqlalchemy").select(SchedulerState)).scalars():
                s.delete(row)
            s.flush()
        with session_scope() as s:
            row = _ensure_scheduler_state(s)
            assert row is not None
            assert row.status == "PAUSED"
            assert row.interval_hours == 6
            assert row.data_source == "SIMULATED"

    def test_persist_run_writes_to_db(self) -> None:
        from techno_service_ai.db import session_scope
        engine = ContinuousDiscoveryEngine()
        result = engine.run_once(
            run_type="MANUAL", data_source_name="SIMULATED", max_candidates=2,
        )
        with session_scope() as s:
            _persist_run(s, result)
            row = s.execute(
                __import__("sqlalchemy").select(ContinuousSearchRun)
                .where(ContinuousSearchRun.run_id == result.run_id)
            ).scalars().first()
            assert row is not None
            assert row.run_type == "MANUAL"
            assert row.n_candidates_surfaced == 2

    def test_persist_candidates_writes_to_db(self) -> None:
        from techno_service_ai.db import session_scope
        engine = ContinuousDiscoveryEngine()
        result = engine.run_once(
            run_type="MANUAL", data_source_name="SIMULATED", max_candidates=2,
        )
        with session_scope() as s:
            _persist_candidates(s, result)
            rows = s.execute(
                __import__("sqlalchemy").select(ContinuousDiscoveryCandidate)
                .where(ContinuousDiscoveryCandidate.run_id == result.run_id)
            ).scalars().all()
            assert len(rows) == 2

    def test_persist_notifications_writes_to_db(self) -> None:
        from techno_service_ai.db import session_scope
        engine = ContinuousDiscoveryEngine()
        result = engine.run_once(
            run_type="MANUAL", data_source_name="SIMULATED", max_candidates=5,
        )
        with session_scope() as s:
            _persist_notifications(s, result.notifications)
            rows = s.execute(
                __import__("sqlalchemy").select(ContinuousDiscoveryNotification)
            ).scalars().all()
            assert len(rows) == len(result.notifications)
            for r in rows:
                assert r.subject_en
                assert r.subject_ar
                assert r.delivered is True


# ===========================================================================
# Scheduler lifecycle
# ===========================================================================


class TestScheduler:
    def setup_method(self) -> None:
        # Each test gets a fresh scheduler.
        self.sched = InProcessScheduler()

    def teardown_method(self) -> None:
        # Always stop the thread to avoid leaks.
        try:
            self.sched.stop(updated_by="test")
        except Exception:
            pass

    def test_initial_status_not_running(self) -> None:
        s = self.sched.status()
        assert s["running"] is False
        assert s["paused"] is False

    def test_start_creates_thread_and_state(self) -> None:
        self.sched.start(interval_hours=1, data_source="SIMULATED")
        assert self.sched.status()["running"] is True
        from techno_service_ai.db import session_scope
        with session_scope() as s:
            state = _ensure_scheduler_state(s)
            assert state.status == "RUNNING"
            assert state.interval_hours == 1
            assert state.data_source == "SIMULATED"

    def test_pause_and_resume(self) -> None:
        self.sched.start(interval_hours=1)
        self.sched.pause()
        assert self.sched.status()["paused"] is True
        from techno_service_ai.db import session_scope
        with session_scope() as s:
            state = _ensure_scheduler_state(s)
            assert state.status == "PAUSED"
        self.sched.resume()
        assert self.sched.status()["paused"] is False
        with session_scope() as s:
            state = _ensure_scheduler_state(s)
            assert state.status == "RUNNING"

    def test_update_interval(self) -> None:
        self.sched.start(interval_hours=6)
        self.sched.update_interval(12)
        from techno_service_ai.db import session_scope
        with session_scope() as s:
            state = _ensure_scheduler_state(s)
            assert state.interval_hours == 12

    def test_update_data_source(self) -> None:
        self.sched.start(interval_hours=6, data_source="SIMULATED")
        # SIMULATED is the only available source; this should still
        # update the field even if the engine falls back.
        self.sched.update_data_source("SIMULATED")
        from techno_service_ai.db import session_scope
        with session_scope() as s:
            state = _ensure_scheduler_state(s)
            assert state.data_source == "SIMULATED"

    def test_manual_trigger_persists_run(self) -> None:
        self.sched.start(interval_hours=6)
        result = self.sched.trigger_manual(triggered_by="tester", max_candidates=2)
        assert result.status == RunStatus.COMPLETED
        assert len(result.evaluated) == 2
        from techno_service_ai.db import session_scope
        with session_scope() as s:
            row = s.execute(
                __import__("sqlalchemy").select(ContinuousSearchRun)
                .where(ContinuousSearchRun.run_id == result.run_id)
            ).scalars().first()
            assert row is not None
            assert row.triggered_by == "tester"
            assert row.run_type == "MANUAL"

    def test_manual_trigger_works_when_paused(self) -> None:
        # Scheduler is paused but manual trigger still works.
        result = self.sched.trigger_manual(triggered_by="tester", max_candidates=1)
        assert result.status == RunStatus.COMPLETED

    def test_stop_ends_thread(self) -> None:
        self.sched.start(interval_hours=1)
        assert self.sched.status()["running"] is True
        self.sched.stop()
        assert self.sched.status()["running"] is False
        from techno_service_ai.db import session_scope
        with session_scope() as s:
            state = _ensure_scheduler_state(s)
            assert state.status == "PAUSED"


# ===========================================================================
# Routes (HTTP)
# ===========================================================================


class TestRoutes:
    def _login_admin(self, client) -> None:
        r = client.post(
            "/sign-in",
            data={"username": "admin", "password": "ChangeMe!2026"},
            follow_redirects=False,
        )
        assert r.status_code == 303, f"sign-in failed: status={r.status_code} body={r.text[:200]}"

    def _set_lang(self, client, lang: str) -> None:
        """Set the language cookie on the test client (the i18n
        middleware reads the cookie, not query params)."""
        client.cookies.set("tsai_lang", lang)

    def test_console_route_renders_english(self) -> None:
        from fastapi.testclient import TestClient
        from techno_service_ai.app import create_app
        app = create_app()
        with TestClient(app) as client:
            self._login_admin(client)
            r = client.get("/phase9/continuous-discovery/console?lang=en")
            assert r.status_code == 200
            assert "Continuous Proactive Discovery Console" in r.text
            assert 'dir="ltr"' in r.text or 'lang="en"' in r.text

    def test_console_route_renders_arabic(self) -> None:
        from fastapi.testclient import TestClient
        from techno_service_ai.app import create_app
        app = create_app()
        with TestClient(app) as client:
            self._login_admin(client)
            self._set_lang(client, "ar")
            r = client.get("/phase9/continuous-discovery/console")
            assert r.status_code == 200
            assert 'dir="rtl"' in r.text
            assert 'lang="ar"' in r.text
            assert "وحدة تحكم الاكتشاف" in r.text

    def test_settings_route_renders_arabic(self) -> None:
        from fastapi.testclient import TestClient
        from techno_service_ai.app import create_app
        app = create_app()
        with TestClient(app) as client:
            self._login_admin(client)
            self._set_lang(client, "ar")
            r = client.get("/phase9/continuous-discovery/settings")
            assert r.status_code == 200
            assert "إعدادات الاكتشاف" in r.text

    def test_history_route_renders_english(self) -> None:
        from fastapi.testclient import TestClient
        from techno_service_ai.app import create_app
        app = create_app()
        with TestClient(app) as client:
            self._login_admin(client)
            r = client.get("/phase9/continuous-discovery/history?lang=en")
            assert r.status_code == 200
            assert "Continuous Discovery Run History" in r.text

    def test_manual_trigger_endpoint(self) -> None:
        from fastapi.testclient import TestClient
        from techno_service_ai.app import create_app
        app = create_app()
        with TestClient(app) as client:
            self._login_admin(client)
            r = client.post("/phase9/continuous-discovery/trigger", follow_redirects=False)
            assert r.status_code == 303
            assert "/phase9/continuous-discovery/console" in r.headers.get("location", "")

    def test_pause_resume_endpoints(self) -> None:
        from fastapi.testclient import TestClient
        from techno_service_ai.app import create_app
        app = create_app()
        with TestClient(app) as client:
            self._login_admin(client)
            r = client.post("/phase9/continuous-discovery/pause", follow_redirects=False)
            assert r.status_code == 303
            r = client.post("/phase9/continuous-discovery/resume", follow_redirects=False)
            assert r.status_code == 303

    def test_start_stop_endpoints(self) -> None:
        from fastapi.testclient import TestClient
        from techno_service_ai.app import create_app
        app = create_app()
        with TestClient(app) as client:
            self._login_admin(client)
            r = client.post("/phase9/continuous-discovery/start", follow_redirects=False)
            assert r.status_code == 303
            r = client.post("/phase9/continuous-discovery/stop", follow_redirects=False)
            assert r.status_code == 303

    def test_settings_post_updates_state(self) -> None:
        from fastapi.testclient import TestClient
        from techno_service_ai.app import create_app
        from techno_service_ai.db import session_scope
        from techno_service_ai.phase2_schema import SchedulerState
        app = create_app()
        with TestClient(app) as client:
            self._login_admin(client)
            r = client.post(
                "/phase9/continuous-discovery/settings",
                data={"interval_hours": "12", "data_source": "SIMULATED"},
                follow_redirects=False,
            )
            assert r.status_code == 303
            with session_scope() as s:
                state = s.execute(
                    __import__("sqlalchemy").select(SchedulerState)
                ).scalars().first()
                assert state is not None
                assert state.interval_hours == 12


# ===========================================================================
# Notification integration
# ===========================================================================


class TestNotificationIntegration:
    def test_qualified_candidate_creates_bilingual_notification(self) -> None:
        engine = ContinuousDiscoveryEngine()
        result = engine.run_once(
            run_type="MANUAL", data_source_name="SIMULATED", max_candidates=5,
        )
        qualified = [c for c in result.evaluated if c.overall == CandidateStatus.QUALIFIED]
        assert qualified, "expected at least one qualified candidate in DEMO run"
        for c in qualified:
            n = next((n for n in result.notifications if n.candidate_id == c.candidate_id), None)
            assert n is not None
            assert c.product_name in n.subject_en
            assert c.manufacturer_name in n.body_en
            assert c.manufacturer_name in n.body_ar
            assert n.priority == "CLASS_3"
            assert "مرشح جديد" in n.body_ar

    def test_rejected_candidate_no_notification(self) -> None:
        engine = ContinuousDiscoveryEngine()
        result = engine.run_once(
            run_type="MANUAL", data_source_name="SIMULATED", max_candidates=5,
        )
        rejected = [c for c in result.evaluated if c.overall == CandidateStatus.REJECTED]
        for c in rejected:
            n = next((n for n in result.notifications if n.candidate_id == c.candidate_id), None)
            assert n is None
