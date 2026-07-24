from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.repositories.audit_logs import create_audit_log
from app.repositories.submissions import (
    get_judge_logs_by_submission_id,
    get_judge_logs_paginated,
    get_submission_by_id,
)
from app.utils.dependencies import get_current_user, require_teacher
from app.utils.log_views import to_student_log_view, to_teacher_log_view
from app.utils.responses import success_response
from app.utils.time import to_utc_iso

router = APIRouter(tags=["logs"])


@router.get("/api/submissions/{submission_id}/logs")
async def get_submission_logs(
    submission_id: str,
    current_user=Depends(get_current_user),
):
    submission = get_submission_by_id(submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="submission not found")
    if (
        current_user["role"] == "student"
        and submission["user_id"] != current_user["id"]
    ):
        raise HTTPException(status_code=403, detail="access not allowed")

    logs = get_judge_logs_by_submission_id(submission_id)
    full_access = current_user["role"] in ("teacher", "admin")

    if full_access:
        create_audit_log(
            operator_id=current_user["id"],
            action="VIEW_FULL_JUDGE_LOG",
            target_type="submission",
            target_id=submission_id,
            success=True,
            detail={"log_count": len(logs)},
        )

    serializer = to_teacher_log_view if full_access else to_student_log_view
    return success_response(data=[serializer(log) for log in logs])


@router.get("/api/logs")
async def list_all_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    submission_id: str | None = None,
    problem_id: str | None = None,
    user_id: str | None = None,
    result: Literal["AC", "WA", "RE", "TLE", "SE"] | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    current_user=Depends(require_teacher),
):
    logs, total = get_judge_logs_paginated(
        page=page,
        page_size=page_size,
        submission_id=submission_id,
        problem_id=problem_id,
        user_id=user_id,
        result=result,
        start_time=to_utc_iso(start_time),
        end_time=to_utc_iso(end_time),
    )

    create_audit_log(
        operator_id=current_user["id"],
        action="VIEW_FULL_JUDGE_LOG",
        target_type="judge_log_query",
        target_id=submission_id or "all",
        success=True,
        detail={
            "page": page,
            "page_size": page_size,
            "submission_id": submission_id,
            "problem_id": problem_id,
            "user_id": user_id,
            "result": result,
        },
    )

    items = []
    for log in logs:
        item = to_teacher_log_view(log)
        item["problem_id"] = log["problem_id"]
        item["user_id"] = log["user_id"]
        items.append(item)

    return success_response(
        data={
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )
