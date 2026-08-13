from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_qa_dashboard_enabled
from app.db.session import get_db
from app.models.tenant import User
from app.schemas.qa import (
    QAAutomatedRunResponse,
    QAFileDefectResponse,
    QADefectCreateRequest,
    QADefectResponse,
    QADefectUpdateRequest,
    QAOverviewResponse,
    QATestCaseResponse,
    QATestCaseUpdateRequest,
    QATestCycleCreateRequest,
    QATestCycleDetail,
    QATestCycleSummary,
    QATestCycleUpdateRequest,
)
from app.schemas.red_team import RedTeamCampaignResponse
from app.services import qa_service
from app.services.red_team_service import campaign_csv, run_campaign

router = APIRouter(dependencies=[Depends(require_qa_dashboard_enabled)])

# QA is available to authenticated tenant users when the module is enabled.


@router.get("/qa/red-team/run", response_model=RedTeamCampaignResponse)
async def run_red_team_campaign(
    _current_user: Annotated[User, Depends(require_qa_dashboard_enabled)],
) -> RedTeamCampaignResponse:
    return run_campaign()


@router.get("/qa/red-team/export")
async def export_red_team_campaign(
    _current_user: Annotated[User, Depends(require_qa_dashboard_enabled)],
    format: str = Query(default="csv", pattern="^(csv|json)$"),
) -> Response:
    report = run_campaign()
    if format == "json":
        return Response(
            content=report.model_dump_json(indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=pysetuai-red-team-report.json"},
        )
    return Response(
        content=campaign_csv(report),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pysetuai-red-team-report.csv"},
    )


@router.get("/qa/overview", response_model=QAOverviewResponse)
async def get_qa_overview(
    current_user: Annotated[User, Depends(require_qa_dashboard_enabled)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QAOverviewResponse:
    data = await qa_service.build_overview(db, current_user.tenant_id)
    active = data.pop("active_cycle")
    return QAOverviewResponse(
        active_cycle=QATestCycleSummary(**active) if active else None,
        **data,
    )


@router.get("/qa/cycles", response_model=list[QATestCycleSummary])
async def list_qa_cycles(
    current_user: Annotated[User, Depends(require_qa_dashboard_enabled)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(20, ge=1, le=100),
) -> list[QATestCycleSummary]:
    rows = await qa_service.list_cycles(db, current_user.tenant_id, limit=limit)
    return [QATestCycleSummary(**qa_service.cycle_summary(cycle, cases)) for cycle, cases in rows]


@router.post("/qa/cycles", response_model=QATestCycleDetail, status_code=status.HTTP_201_CREATED)
async def create_qa_cycle(
    payload: QATestCycleCreateRequest,
    current_user: Annotated[User, Depends(require_qa_dashboard_enabled)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QATestCycleDetail:
    cycle, cases = await qa_service.create_cycle(
        db,
        current_user,
        payload.name,
        import_baseline=payload.import_baseline,
        import_baseline_defects=payload.import_baseline_defects,
    )
    summary = qa_service.cycle_summary(cycle, cases)
    return QATestCycleDetail(
        **summary,
        cases=[QATestCaseResponse(**qa_service.case_dict(c)) for c in cases],
    )


@router.get("/qa/cycles/{cycle_id}", response_model=QATestCycleDetail)
async def get_qa_cycle(
    cycle_id: str,
    current_user: Annotated[User, Depends(require_qa_dashboard_enabled)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QATestCycleDetail:
    row = await qa_service.get_cycle(db, current_user.tenant_id, cycle_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")
    cycle, cases = row
    return QATestCycleDetail(
        **qa_service.cycle_summary(cycle, cases),
        cases=[QATestCaseResponse(**qa_service.case_dict(c)) for c in cases],
    )


@router.patch("/qa/cycles/{cycle_id}", response_model=QATestCycleSummary)
async def update_qa_cycle(
    cycle_id: str,
    payload: QATestCycleUpdateRequest,
    current_user: Annotated[User, Depends(require_qa_dashboard_enabled)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QATestCycleSummary:
    cycle = await qa_service.update_cycle(
        db,
        current_user.tenant_id,
        cycle_id,
        status=payload.status,
        release_decision=payload.release_decision,
        notes=payload.notes,
    )
    if cycle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")
    row = await qa_service.get_cycle(db, current_user.tenant_id, cycle_id)
    assert row is not None
    _, cases = row
    return QATestCycleSummary(**qa_service.cycle_summary(cycle, cases))


@router.patch("/qa/test-cases/{case_id}", response_model=QATestCaseResponse)
async def update_qa_test_case(
    case_id: str,
    payload: QATestCaseUpdateRequest,
    current_user: Annotated[User, Depends(require_qa_dashboard_enabled)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QATestCaseResponse:
    case = await qa_service.update_test_case(
        db,
        current_user.tenant_id,
        case_id,
        current_user,
        status=payload.status,
        notes=payload.notes,
    )
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found")
    return QATestCaseResponse(**qa_service.case_dict(case))


@router.get("/qa/defects", response_model=list[QADefectResponse])
async def list_qa_defects(
    current_user: Annotated[User, Depends(require_qa_dashboard_enabled)],
    db: Annotated[AsyncSession, Depends(get_db)],
    cycle_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> list[QADefectResponse]:
    rows = await qa_service.list_defects(db, current_user.tenant_id, cycle_id=cycle_id, status=status)
    return [QADefectResponse(**qa_service.defect_dict(d, code)) for d, code in rows]


@router.post("/qa/defects", response_model=QADefectResponse, status_code=status.HTTP_201_CREATED)
async def create_qa_defect(
    payload: QADefectCreateRequest,
    current_user: Annotated[User, Depends(require_qa_dashboard_enabled)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QADefectResponse:
    defect = await qa_service.create_defect(db, current_user, payload.model_dump())
    linked_code = None
    if defect.linked_case_id:
        row = await qa_service.get_cycle(db, current_user.tenant_id, str(defect.cycle_id)) if defect.cycle_id else None
        if row:
            _, cases = row
            linked_code = next((c.case_id for c in cases if c.id == defect.linked_case_id), None)
    return QADefectResponse(**qa_service.defect_dict(defect, linked_code))


@router.patch("/qa/defects/{defect_id}", response_model=QADefectResponse)
async def update_qa_defect(
    defect_id: str,
    payload: QADefectUpdateRequest,
    current_user: Annotated[User, Depends(require_qa_dashboard_enabled)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QADefectResponse:
    defect = await qa_service.update_defect(
        db,
        current_user.tenant_id,
        defect_id,
        payload.model_dump(exclude_unset=True),
    )
    if defect is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Defect not found")
    return QADefectResponse(**qa_service.defect_dict(defect))


@router.get("/qa/next-defect-code")
async def get_next_defect_code(
    current_user: Annotated[User, Depends(require_qa_dashboard_enabled)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    code = await qa_service.next_defect_code(db, current_user.tenant_id)
    return {"defect_code": code}


@router.post("/qa/test-cases/{case_id}/file-defect", response_model=QAFileDefectResponse)
async def file_defect_from_failed_case(
    case_id: str,
    current_user: Annotated[User, Depends(require_qa_dashboard_enabled)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QAFileDefectResponse:
    try:
        defect, linked_code, created = await qa_service.create_defect_from_failed_case(
            db, current_user.tenant_id, current_user, case_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return QAFileDefectResponse(
        defect=QADefectResponse(**qa_service.defect_dict(defect, linked_code)),
        created=created,
    )


@router.post("/qa/cycles/{cycle_id}/run-automated", response_model=QAAutomatedRunResponse)
async def run_qa_automated_tests(
    cycle_id: str,
    current_user: Annotated[User, Depends(require_qa_dashboard_enabled)],
    db: Annotated[AsyncSession, Depends(get_db)],
    scope: str = Query(default="all", pattern="^(all|failed)$"),
) -> QAAutomatedRunResponse:
    try:
        result = await qa_service.run_automated_tests(
            db,
            current_user.tenant_id,
            cycle_id,
            current_user,
            scope=scope,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return QAAutomatedRunResponse(**result)
