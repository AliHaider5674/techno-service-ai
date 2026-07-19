"""In-process scheduler for Continuous Proactive Discovery.

Per the Sprint Brief and the Constitutional Owner's directive
(2026-07-19), this scheduler uses Python's standard library
`threading` module. APScheduler is not installed; the in-process
implementation is a constitutional-equivalent for the demo. A
production migration to APScheduler (or a proper scheduler) is a
HD-PHASE8 operational gate, not a constitutional requirement.

Recorded as ASS-PHASE9-001 in the Decision & Assumption Register.

Design:
  - The scheduler runs a background thread that sleeps for the
    configured interval, then runs one ContinuousDiscoveryEngine.
  - The scheduler can be PAUSED (thread sleeps but does not run)
    or RUNNING.
  - The interval (in hours) is configurable per Constitutional
    Owner.
  - A manual trigger is always available and does not require the
    schedule to be running.
  - All run results are persisted by the integration layer
    (phase9_continuous_routes.py), not the scheduler itself.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import db
from .continuous_discovery import (
    ContinuousDiscoveryEngine,
    NotificationRecord,
    RunResult,
    RunStatus,
)
from .phase2_schema import (
    ConflictDoNotPursueEntity,
    ContinuousDiscoveryCandidate,
    ContinuousDiscoveryNotification,
    ContinuousSearchRun,
    RepresentedPrincipal,
    RestrictedProhibitedEntity,
    SchedulerState,
)


log = logging.getLogger("tsai.scheduler")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_register_brands(db_session: Session) -> tuple:
    """Load the active entries of the 3 Constitutional Registers.

    Returns three lists: (represented_brands, conflict_brands,
    restricted_brands). Used by the engine layer's register check.
    """
    represented = [
        r.brand
        for r in db_session.execute(
            select(RepresentedPrincipal).where(RepresentedPrincipal.status == "ACTIVE")
        ).scalars()
    ]
    conflict = [
        r.entity_name
        for r in db_session.execute(
            select(ConflictDoNotPursueEntity).where(ConflictDoNotPursueEntity.status == "ACTIVE")
        ).scalars()
    ]
    restricted = [
        r.entity_name
        for r in db_session.execute(
            select(RestrictedProhibitedEntity).where(RestrictedProhibitedEntity.status == "ACTIVE")
        ).scalars()
    ]
    return represented, conflict, restricted


def _persist_run(db_session: Session, result: RunResult) -> ContinuousSearchRun:
    """Persist a RunResult to IMPL-002 (ContinuousSearchRun)."""
    row = ContinuousSearchRun(
        run_id=result.run_id,
        run_type=result.run_type,
        data_source=result.data_source,
        started_at=result.started_at,
        finished_at=result.finished_at,
        status=result.status.value,
        n_agents_activated=result.n_agents_activated,
        n_candidates_surfaced=len(result.evaluated),
        n_qualified=sum(1 for c in result.evaluated if c.overall.value == "QUALIFIED"),
        n_rejected=sum(1 for c in result.evaluated if c.overall.value == "REJECTED"),
        n_notifications_sent=len(result.notifications),
        error_message=result.error_message,
        triggered_by=result.triggered_by,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _persist_candidates(
    db_session: Session,
    result: RunResult,
) -> List[ContinuousDiscoveryCandidate]:
    """Persist each evaluated candidate to IMPL-003."""
    rows: List[ContinuousDiscoveryCandidate] = []
    for ev in result.evaluated:
        row = ContinuousDiscoveryCandidate(
            candidate_id=ev.candidate_id,
            product_name=ev.product_name,
            product_category=ev.product_category,
            sector=ev.sector,
            manufacturer_name=ev.manufacturer_name,
            manufacturer_country=ev.manufacturer_country,
            data_source=ev.data_source,
            data_source_marker=ev.data_source_marker,
            source_citation_url=ev.source_citation_url,
            signal_strength=ev.signal_strength,
            f1_pass=ev.filters.f1_kuwait_climate,
            f1_rationale=ev.filters.f1_rationale,
            f2_pass=ev.filters.f2_retrofit,
            f2_rationale=ev.filters.f2_rationale,
            f3_pass=ev.filters.f3_no_agent_kuwait,
            f3_rationale=ev.filters.f3_rationale,
            f4_pass=ev.filters.f4_low_operating_cost,
            f4_rationale=ev.filters.f4_rationale,
            f5_pass=ev.filters.f5_company_size,
            f5_rationale=ev.filters.f5_rationale,
            register_check="PASS" if ev.register.passed else "FAIL",
            register_finding=ev.register.finding,
            overall=ev.overall.value,
            discovered_at=ev.discovered_at,
            run_id=result.run_id,
        )
        db_session.add(row)
        rows.append(row)
    db_session.flush()
    return rows


def _persist_notifications(
    db_session: Session,
    notifications: List[NotificationRecord],
) -> List[ContinuousDiscoveryNotification]:
    """Persist each notification to IMPL-004.

    Also creates a row in the constitutional Notification table
    (used by the Notification Center) so the message appears in
    the UI immediately.
    """
    rows: List[ContinuousDiscoveryNotification] = []
    for n in notifications:
        row = ContinuousDiscoveryNotification(
            notification_id=n.notification_id,
            candidate_id=n.candidate_id,
            run_id=n.run_id,
            subject_en=n.subject_en,
            subject_ar=n.subject_ar,
            body_en=n.body_en,
            body_ar=n.body_ar,
            priority=n.priority,
            created_at=n.created_at,
            delivered=True,
        )
        db_session.add(row)
        rows.append(row)
    db_session.flush()
    return rows


def _ensure_scheduler_state(db_session: Session) -> SchedulerState:
    """Ensure the SchedulerState singleton exists (creates it on first run)."""
    row = db_session.execute(select(SchedulerState).order_by(SchedulerState.id)).scalars().first()
    if row is None:
        row = SchedulerState(
            status="PAUSED",
            interval_hours=6,
            data_source="SIMULATED",
            last_run_at=None,
            next_run_at=None,
            updated_at=_now(),
            updated_by="system",
        )
        db_session.add(row)
        db_session.flush()
    return row


# ---------------------------------------------------------------------------
# In-process threading scheduler
# ---------------------------------------------------------------------------


class InProcessScheduler:
    """A simple in-process threading scheduler.

    The scheduler runs a single daemon thread that loops, sleeping
    for the configured interval, then running one
    ContinuousDiscoveryEngine. PAUSE stops the thread from running
    new jobs but does not interrupt the current one.
    """

    def __init__(self) -> None:
        self._engine = ContinuousDiscoveryEngine()
        self._thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()
        self._pause_flag = threading.Event()
        self._lock = threading.Lock()

    # ----- status -----

    def status(self) -> dict:
        with self._lock:
            return {
                "running": self._thread is not None and self._thread.is_alive(),
                "paused": self._pause_flag.is_set(),
            }

    # ----- control -----

    def start(self, interval_hours: int = 6, data_source: str = "SIMULATED", updated_by: str = "system") -> None:
        """Start the background scheduler thread.

        If the thread is already running, this is a no-op. The
        interval is read from SchedulerState at each iteration
        so subsequent updates to the interval take effect on the
        next loop.
        """
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            # Reset the stop flag and clear the pause flag.
            self._stop_flag.clear()
            self._pause_flag.clear()
            # Persist the requested interval + data source.
            with db.session_scope() as s:
                state = _ensure_scheduler_state(s)
                state.status = "RUNNING"
                state.interval_hours = max(1, int(interval_hours))
                state.data_source = data_source
                state.updated_at = _now()
                state.updated_by = updated_by
                state.next_run_at = _now() + timedelta(hours=state.interval_hours)
            # Start the thread.
            self._thread = threading.Thread(
                target=self._loop,
                name="tsai-continuous-discovery-scheduler",
                daemon=True,
            )
            self._thread.start()
            log.info("Scheduler started: interval=%dh source=%s", interval_hours, data_source)

    def stop(self, updated_by: str = "system") -> None:
        """Stop the background scheduler thread.

        Waits up to 5 seconds for the thread to exit. If the
        thread is not running, this is a no-op.
        """
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                # Still update the DB so the UI reflects the state.
                with db.session_scope() as s:
                    state = _ensure_scheduler_state(s)
                    state.status = "PAUSED"
                    state.updated_at = _now()
                    state.updated_by = updated_by
                return
            self._stop_flag.set()
            self._pause_flag.clear()
        self._thread.join(timeout=5.0)
        with db.session_scope() as s:
            state = _ensure_scheduler_state(s)
            state.status = "PAUSED"
            state.updated_at = _now()
            state.updated_by = updated_by
            state.next_run_at = None
        log.info("Scheduler stopped")

    def pause(self, updated_by: str = "system") -> None:
        """Pause the scheduler (the thread keeps running but skips runs)."""
        with self._lock:
            self._pause_flag.set()
            with db.session_scope() as s:
                state = _ensure_scheduler_state(s)
                state.status = "PAUSED"
                state.updated_at = _now()
                state.updated_by = updated_by
                state.next_run_at = None
        log.info("Scheduler paused")

    def resume(self, updated_by: str = "system") -> None:
        """Resume the scheduler (thread will run again on next loop)."""
        with self._lock:
            self._pause_flag.clear()
            with db.session_scope() as s:
                state = _ensure_scheduler_state(s)
                state.status = "RUNNING"
                state.updated_at = _now()
                state.updated_by = updated_by
                state.next_run_at = _now() + timedelta(hours=state.interval_hours)
        log.info("Scheduler resumed")

    def update_interval(self, interval_hours: int, updated_by: str = "system") -> None:
        """Update the configured interval. Next loop reads this."""
        with db.session_scope() as s:
            state = _ensure_scheduler_state(s)
            state.interval_hours = max(1, int(interval_hours))
            state.updated_at = _now()
            state.updated_by = updated_by
            if state.status == "RUNNING":
                state.next_run_at = _now() + timedelta(hours=state.interval_hours)
        log.info("Scheduler interval updated: %dh", interval_hours)

    def update_data_source(self, data_source: str, updated_by: str = "system") -> None:
        """Update the data source identifier. The next run uses it."""
        with db.session_scope() as s:
            state = _ensure_scheduler_state(s)
            state.data_source = data_source
            state.updated_at = _now()
            state.updated_by = updated_by
        log.info("Scheduler data source updated: %s", data_source)

    # ----- manual trigger -----

    def trigger_manual(self, triggered_by: str = "system", max_candidates: int = 5) -> RunResult:
        """Run one Continuous Discovery synchronously.

        Does not depend on the schedule status. Returns the
        RunResult. The integration layer is responsible for
        persisting the result and triggering any UI side-effects.
        """
        # Read the current data source from the scheduler state.
        with db.session_scope() as s:
            state = _ensure_scheduler_state(s)
            data_source = state.data_source
            interval = state.interval_hours

        represented, conflict, restricted = [], [], []
        with db.session_scope() as s:
            represented, conflict, restricted = _load_register_brands(s)

        result = self._engine.run_once(
            run_type="MANUAL",
            data_source_name=data_source,
            max_candidates=max_candidates,
            represented_brands=represented,
            conflict_brands=conflict,
            restricted_brands=restricted,
            triggered_by=triggered_by,
        )

        # Persist + update state.
        with db.session_scope() as s:
            _persist_run(s, result)
            _persist_candidates(s, result)
            _persist_notifications(s, result.notifications)
            state = _ensure_scheduler_state(s)
            state.last_run_at = result.finished_at
            if state.status == "RUNNING":
                state.next_run_at = result.finished_at + timedelta(hours=interval)
            state.updated_at = _now()
        return result

    # ----- thread loop -----

    def _loop(self) -> None:
        """Background thread: sleep, then run, then sleep, ... .

        The loop is the only place the scheduler initiates a run.
        On each iteration:
          - Read interval + data source from SchedulerState.
          - If pause_flag is set, sleep a short interval and continue.
          - If stop_flag is set, exit.
          - Otherwise, run one Continuous Discovery, then sleep.
        """
        while not self._stop_flag.is_set():
            # Read current state.
            with db.session_scope() as s:
                state = _ensure_scheduler_state(s)
                interval = state.interval_hours
                data_source = state.data_source

            if self._pause_flag.is_set():
                # Paused: short sleep and continue.
                if self._stop_flag.wait(timeout=10.0):
                    return
                continue

            # Run one discovery.
            try:
                represented, conflict, restricted = [], [], []
                with db.session_scope() as s:
                    represented, conflict, restricted = _load_register_brands(s)

                result = self._engine.run_once(
                    run_type="SCHEDULED",
                    data_source_name=data_source,
                    max_candidates=5,
                    represented_brands=represented,
                    conflict_brands=conflict,
                    restricted_brands=restricted,
                    triggered_by="scheduler",
                )
                with db.session_scope() as s:
                    _persist_run(s, result)
                    _persist_candidates(s, result)
                    _persist_notifications(s, result.notifications)
                    state = _ensure_scheduler_state(s)
                    state.last_run_at = result.finished_at
                    state.next_run_at = result.finished_at + timedelta(hours=interval)
                    state.updated_at = _now()
            except Exception as exc:  # noqa: BLE001
                log.error("Scheduler run failed: %s", exc, exc_info=True)

            # Sleep until the next interval (in 10s slices so we
            # respond quickly to pause/stop).
            slept = 0.0
            while slept < interval * 3600.0:
                if self._stop_flag.is_set():
                    return
                if self._pause_flag.wait(timeout=10.0):
                    # Pause was signalled mid-sleep.
                    break
                slept += 10.0


# ---------------------------------------------------------------------------
# Module-level singleton (lazy).
# ---------------------------------------------------------------------------

_INSTANCE: Optional[InProcessScheduler] = None


def get_scheduler() -> InProcessScheduler:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = InProcessScheduler()
    return _INSTANCE
