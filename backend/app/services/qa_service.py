from __future__ import annotations

import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.qa import QADefect, QATestCase, QATestCycle
from app.models.tenant import User
from app.services.qa_test_catalog import BASELINE_DEFECTS, CASE_GUIDANCE, TEST_CASE_CATALOG


def _cycle_counts(cases: list[QATestCase]) -> dict[str, int]:
    counts = {"total": len(cases), "pass": 0, "fail": 0, "blocked": 0, "not_tested": 0, "skipped": 0}
    for case in cases:
        key = case.status if case.status in counts else "not_tested"
        counts[key] = counts.get(key, 0) + 1
    return counts


def cycle_summary(cycle: QATestCycle, cases: list[QATestCase]) -> dict:
    counts = _cycle_counts(cases)
    return {
        "id": str(cycle.id),
        "name": cycle.name,
        "status": cycle.status,
        "release_decision": cycle.release_decision,
        "notes": cycle.notes,
        "started_at": cycle.started_at,
        "completed_at": cycle.completed_at,
        "created_by_name": cycle.created_by_name,
        "created_at": cycle.created_at,
        "total_cases": counts["total"],
        "passed_cases": counts["pass"],
        "failed_cases": counts["fail"],
        "blocked_cases": counts["blocked"],
        "not_tested_cases": counts["not_tested"],
    }


def guidance_for_case(case_id: str) -> dict[str, str | None]:
    meta = CASE_GUIDANCE.get(case_id)
    if meta:
        return dict(meta)
    return {
        "remediation_hint": "Review failure notes, fix root cause in code or config, then retest.",
        "linked_defect_code": None,
        "suggested_severity": "S3",
    }


def case_dict(case: QATestCase) -> dict:
    guidance = guidance_for_case(case.case_id)
    return {
        "id": str(case.id),
        "cycle_id": str(case.cycle_id),
        "case_id": case.case_id,
        "module": case.module,
        "title": case.title,
        "priority": case.priority,
        "method": case.method,
        "status": case.status,
        "notes": case.notes,
        "automated_key": case.automated_key,
        "tested_by_name": case.tested_by_name,
        "tested_at": case.tested_at,
        "remediation_hint": guidance.get("remediation_hint"),
        "linked_defect_code": guidance.get("linked_defect_code"),
        "suggested_severity": guidance.get("suggested_severity"),
    }


def defect_dict(defect: QADefect, linked_case_code: str | None = None) -> dict:
    return {
        "id": str(defect.id),
        "cycle_id": str(defect.cycle_id) if defect.cycle_id else None,
        "linked_case_id": str(defect.linked_case_id) if defect.linked_case_id else None,
        "linked_case_code": linked_case_code,
        "defect_code": defect.defect_code,
        "severity": defect.severity,
        "module": defect.module,
        "title": defect.title,
        "description": defect.description,
        "status": defect.status,
        "created_by_name": defect.created_by_name,
        "created_at": defect.created_at,
        "updated_at": defect.updated_at,
    }


async def list_cycles(db: AsyncSession, tenant_id: uuid.UUID, limit: int = 20) -> list[tuple[QATestCycle, list[QATestCase]]]:
    result = await db.execute(
        select(QATestCycle)
        .where(QATestCycle.tenant_id == tenant_id)
        .order_by(QATestCycle.created_at.desc())
        .limit(limit)
    )
    cycles = list(result.scalars().all())
    output: list[tuple[QATestCycle, list[QATestCase]]] = []
    for cycle in cycles:
        cases_result = await db.execute(select(QATestCase).where(QATestCase.cycle_id == cycle.id))
        output.append((cycle, list(cases_result.scalars().all())))
    return output


async def get_cycle(db: AsyncSession, tenant_id: uuid.UUID, cycle_id: str) -> tuple[QATestCycle, list[QATestCase]] | None:
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        return None
    cycle_result = await db.execute(
        select(QATestCycle).where(QATestCycle.id == cycle_uuid, QATestCycle.tenant_id == tenant_id)
    )
    cycle = cycle_result.scalar_one_or_none()
    if cycle is None:
        return None
    cases_result = await db.execute(
        select(QATestCase).where(QATestCase.cycle_id == cycle.id).order_by(QATestCase.module, QATestCase.case_id)
    )
    return cycle, list(cases_result.scalars().all())


async def create_cycle(
    db: AsyncSession,
    user: User,
    name: str,
    *,
    import_baseline: bool = False,
    import_baseline_defects: bool = False,
) -> tuple[QATestCycle, list[QATestCase]]:
    now = datetime.now(UTC)
    cycle = QATestCycle(
        tenant_id=user.tenant_id,
        name=name.strip(),
        status="in_progress",
        release_decision="pending",
        started_at=now,
        created_by_id=user.id,
        created_by_name=user.name or user.email,
    )
    db.add(cycle)
    await db.flush()

    cases: list[QATestCase] = []
    case_by_code: dict[str, QATestCase] = {}
    for item in TEST_CASE_CATALOG:
        case = QATestCase(
            tenant_id=user.tenant_id,
            cycle_id=cycle.id,
            case_id=item.case_id,
            module=item.module,
            title=item.title,
            priority=item.priority,
            method=item.method,
            automated_key=item.automated_key,
        )
        db.add(case)
        cases.append(case)
        case_by_code[item.case_id] = case

    if import_baseline:
        baseline_status = {
            "SEC-001": "pass",
            "SEC-004": "pass",
            "SEC-009": "pass",
            "AUTH-008": "pass",
            "AUD-007": "pass",
            "POL-010": "pass",
            "POL-011": "pass",
            "AI-001": "pass",
            "AI-004": "pass",
            "MCP-005": "fail",
            "MCP-009": "fail",
            "STU-005": "fail",
            "MT-001": "fail",
            "DASH-001": "pass",
            "POL-001": "pass",
            "LLM-001": "pass",
        }
        for case_id, status in baseline_status.items():
            if case_id in case_by_code:
                case_by_code[case_id].status = status
                case_by_code[case_id].tested_by_name = "QA-001 Baseline"
                case_by_code[case_id].tested_at = now

    if import_baseline_defects:
        for item in BASELINE_DEFECTS:
            linked = case_by_code.get(item.linked_case_id) if item.linked_case_id else None
            db.add(
                QADefect(
                    tenant_id=user.tenant_id,
                    cycle_id=cycle.id,
                    linked_case_id=linked.id if linked else None,
                    defect_code=item.defect_code,
                    severity=item.severity,
                    module=item.module,
                    title=item.title,
                    description=item.description,
                    created_by_name=user.name or user.email,
                )
            )

    await db.commit()
    await db.refresh(cycle)
    for case in cases:
        await db.refresh(case)
    return cycle, cases


async def update_cycle(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    cycle_id: str,
    *,
    status: str | None = None,
    release_decision: str | None = None,
    notes: str | None = None,
) -> QATestCycle | None:
    row = await get_cycle(db, tenant_id, cycle_id)
    if row is None:
        return None
    cycle, _ = row
    if status is not None:
        cycle.status = status
        if status == "in_progress" and cycle.started_at is None:
            cycle.started_at = datetime.now(UTC)
        if status == "completed":
            cycle.completed_at = datetime.now(UTC)
    if release_decision is not None:
        cycle.release_decision = release_decision
    if notes is not None:
        cycle.notes = notes
    await db.commit()
    await db.refresh(cycle)
    return cycle


async def update_test_case(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    case_id: str,
    user: User,
    *,
    status: str,
    notes: str | None = None,
) -> QATestCase | None:
    try:
        case_uuid = uuid.UUID(case_id)
    except ValueError:
        return None
    result = await db.execute(
        select(QATestCase).where(QATestCase.id == case_uuid, QATestCase.tenant_id == tenant_id)
    )
    case = result.scalar_one_or_none()
    if case is None:
        return None
    case.status = status
    if notes is not None:
        case.notes = notes
    case.tested_by_name = user.name or user.email
    case.tested_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(case)
    return case


async def list_defects(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    cycle_id: str | None = None,
    status: str | None = None,
) -> list[tuple[QADefect, str | None]]:
    query = select(QADefect).where(QADefect.tenant_id == tenant_id)
    if cycle_id:
        try:
            query = query.where(QADefect.cycle_id == uuid.UUID(cycle_id))
        except ValueError:
            return []
    if status:
        query = query.where(QADefect.status == status)
    query = query.order_by(QADefect.severity, QADefect.created_at.desc())
    result = await db.execute(query)
    defects = list(result.scalars().all())
    output: list[tuple[QADefect, str | None]] = []
    for defect in defects:
        linked_code = None
        if defect.linked_case_id:
            case_result = await db.execute(select(QATestCase.case_id).where(QATestCase.id == defect.linked_case_id))
            linked_code = case_result.scalar_one_or_none()
        output.append((defect, linked_code))
    return output


async def create_defect_from_failed_case(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user: User,
    case_id: str,
) -> tuple[QADefect, str | None, bool]:
    """Create (or return existing open) defect for a failed test case. Returns (defect, linked_case_code, created)."""
    try:
        case_uuid = uuid.UUID(case_id)
    except ValueError as exc:
        raise ValueError("Invalid test case id") from exc

    result = await db.execute(
        select(QATestCase).where(QATestCase.id == case_uuid, QATestCase.tenant_id == tenant_id)
    )
    case = result.scalar_one_or_none()
    if case is None:
        raise ValueError("Test case not found")
    if case.status != "fail":
        raise ValueError("Only failed test cases can be filed as defects")

    existing = await db.execute(
        select(QADefect).where(
            QADefect.tenant_id == tenant_id,
            QADefect.linked_case_id == case.id,
            QADefect.status == "open",
        )
    )
    open_defect = existing.scalar_one_or_none()
    if open_defect is not None:
        return open_defect, case.case_id, False

    guidance = guidance_for_case(case.case_id)
    defect_code = await next_defect_code(db, tenant_id)
    title = f"Failed: {case.title}"
    if case.notes:
        description = f"{guidance.get('remediation_hint') or ''}\n\nTest notes: {case.notes}".strip()
    else:
        description = guidance.get("remediation_hint") or "Investigate failure, apply fix, and retest."

    defect = QADefect(
        tenant_id=tenant_id,
        cycle_id=case.cycle_id,
        linked_case_id=case.id,
        defect_code=defect_code,
        severity=str(guidance.get("suggested_severity") or "S3"),
        module=case.module,
        title=title[:512],
        description=description,
        created_by_name=user.name or user.email,
    )
    db.add(defect)
    await db.commit()
    await db.refresh(defect)
    return defect, case.case_id, True


async def create_defect(db: AsyncSession, user: User, payload: dict) -> QADefect:
    linked_case_id = None
    if payload.get("linked_case_id"):
        linked_case_id = uuid.UUID(payload["linked_case_id"])
    cycle_id = None
    if payload.get("cycle_id"):
        cycle_id = uuid.UUID(payload["cycle_id"])
    defect = QADefect(
        tenant_id=user.tenant_id,
        cycle_id=cycle_id,
        linked_case_id=linked_case_id,
        defect_code=payload["defect_code"],
        severity=payload["severity"],
        module=payload["module"],
        title=payload["title"],
        description=payload.get("description") or "",
        created_by_name=user.name or user.email,
    )
    db.add(defect)
    await db.commit()
    await db.refresh(defect)
    return defect


async def update_defect(db: AsyncSession, tenant_id: uuid.UUID, defect_id: str, updates: dict) -> QADefect | None:
    try:
        defect_uuid = uuid.UUID(defect_id)
    except ValueError:
        return None
    result = await db.execute(
        select(QADefect).where(QADefect.id == defect_uuid, QADefect.tenant_id == tenant_id)
    )
    defect = result.scalar_one_or_none()
    if defect is None:
        return None
    for key in ("severity", "title", "description", "status"):
        if updates.get(key) is not None:
            setattr(defect, key, updates[key])
    await db.commit()
    await db.refresh(defect)
    return defect


async def build_overview(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    cycles_data = await list_cycles(db, tenant_id, limit=50)
    active = next((c for c, _ in cycles_data if c.status == "in_progress"), None)
    active_cases: list[QATestCase] = []
    if active:
        active_cases = next(cases for c, cases in cycles_data if c.id == active.id)

    open_defects_result = await db.execute(
        select(QADefect).where(QADefect.tenant_id == tenant_id, QADefect.status == "open")
    )
    open_defects = list(open_defects_result.scalars().all())

    tested = [c for c in active_cases if c.status in {"pass", "fail", "blocked", "skipped"}]
    passed = [c for c in active_cases if c.status == "pass"]
    pass_rate = round(len(passed) / len(tested) * 100, 1) if tested else 0.0

    modules = sorted({c.module for c in active_cases}) if active_cases else sorted({c.module for c in TEST_CASE_CATALOG})

    return {
        "active_cycle": cycle_summary(active, active_cases) if active else None,
        "total_cycles": len(cycles_data),
        "total_open_defects": len(open_defects),
        "s1_open_defects": sum(1 for d in open_defects if d.severity == "S1"),
        "s2_open_defects": sum(1 for d in open_defects if d.severity == "S2"),
        "overall_pass_rate": pass_rate,
        "modules_in_scope": modules,
        "release_decision": active.release_decision if active else "pending",
    }


def _parse_pytest_output(output: str) -> dict[str, str]:
    results: dict[str, str] = {}
    for line in output.splitlines():
        line = line.strip()
        if "::" not in line:
            continue
        if " PASSED" in line:
            node = line.split(" PASSED")[0].strip()
            if node.startswith("tests/"):
                results[node] = "pass"
        elif " FAILED" in line:
            node = line.split(" FAILED")[0].strip()
            if node.startswith("tests/"):
                results[node] = "fail"
    return results


def _execute_pytest(test_targets: list[str]) -> subprocess.CompletedProcess[str]:
    backend_root = Path(__file__).resolve().parents[2]
    cmd = ["python", "-m", "pytest", *test_targets, "-v", "--tb=no"]
    return subprocess.run(
        cmd,
        cwd=str(backend_root),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _automated_unavailable_message(reason: str) -> dict:
    return {
        "pytest_exit_code": 127,
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "cases_updated": 0,
        "tests_targeted": 0,
        "scope": "all",
        "output_tail": reason,
    }


async def run_automated_tests(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    cycle_id: str,
    user: User,
    *,
    scope: str = "all",
) -> dict:
    if scope not in {"all", "failed"}:
        raise ValueError("scope must be 'all' or 'failed'")

    row = await get_cycle(db, tenant_id, cycle_id)
    if row is None:
        raise ValueError("Cycle not found")
    _, cases = row
    backend_root = Path(__file__).resolve().parents[2]
    tests_dir = backend_root / "tests"
    if not tests_dir.is_dir():
        return _automated_unavailable_message(
            "Automated tests are unavailable: tests/ directory not found in this deployment."
        )
    try:
        import pytest  # noqa: F401
    except ImportError:
        return _automated_unavailable_message(
            "Automated tests are unavailable: install pytest in the API container (pip install pytest)."
        )

    automatable = [c for c in cases if c.automated_key]
    if scope == "failed":
        automatable = [c for c in automatable if c.status == "fail"]

    if not automatable:
        message = (
            "No failed automatable cases to retest."
            if scope == "failed"
            else "No automatable cases mapped in this cycle."
        )
        return {
            "pytest_exit_code": 0,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "cases_updated": 0,
            "tests_targeted": 0,
            "scope": scope,
            "output_tail": message,
        }

    test_targets = (
        sorted({case.automated_key for case in automatable if case.automated_key})
        if scope == "failed"
        else ["tests/"]
    )
    proc = _execute_pytest(test_targets)
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    parsed = _parse_pytest_output(output)
    now = datetime.now(UTC)
    updated = 0
    target_keys = {case.automated_key for case in automatable if case.automated_key}
    for case in cases:
        if not case.automated_key or case.automated_key not in target_keys:
            continue
        status = parsed.get(case.automated_key)
        if status is None:
            continue
        case.status = status
        case.tested_by_name = user.name or user.email
        case.tested_at = now
        case.notes = f"Automated run ({scope}) exit={proc.returncode}"
        updated += 1
    await db.commit()

    passed = sum(1 for key, value in parsed.items() if key in target_keys and value == "pass")
    failed = sum(1 for key, value in parsed.items() if key in target_keys and value == "fail")
    tail = "\n".join(output.splitlines()[-15:])
    return {
        "pytest_exit_code": proc.returncode,
        "tests_run": len([k for k in parsed if k in target_keys]),
        "tests_passed": passed,
        "tests_failed": failed,
        "cases_updated": updated,
        "tests_targeted": len(test_targets) if scope == "failed" else len(target_keys),
        "scope": scope,
        "output_tail": tail,
    }


async def next_defect_code(db: AsyncSession, tenant_id: uuid.UUID) -> str:
    result = await db.execute(
        select(func.count()).select_from(QADefect).where(QADefect.tenant_id == tenant_id)
    )
    count = result.scalar_one() or 0
    return f"DEF-{count + 1:03d}"
