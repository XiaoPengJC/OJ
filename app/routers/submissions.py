from datetime import datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from app.models.submission import SubmissionCreateRequest
from app.repositories.audit_logs import create_audit_log
from app.repositories.problems import get_problem_by_id
from app.repositories.submissions import (
    create_submission,
    get_submission_by_id,
    get_submissions_paginated,
    reset_submission_for_rejudge,
)
from app.services.judge_service import process_submission
from app.utils.dependencies import get_current_user, require_teacher
from app.utils.responses import success_response
from app.utils.time import to_utc_iso

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


def serialize_submission(submission, include_source: bool = False) -> dict:
    data = {
        "id": submission["id"],
        "user_id": submission["user_id"],
        "problem_id": submission["problem_id"],
        "language": submission["language"],
        "status": submission["status"],
        "result": submission["result"],
        "score": submission["score"],
        "total_time": submission["total_time"],
        "created_at": submission["created_at"],
        "started_at": submission["started_at"],
        "finished_at": submission["finished_at"],
    }
    if include_source:
        data["source_code"] = submission["source_code"]
    return data


@router.post("", status_code=202)
async def submit_solution(
    data: SubmissionCreateRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
):
    if get_problem_by_id(data.problem_id) is None:
        raise HTTPException(status_code=404, detail="problem not found")

    submission = create_submission(data, current_user["id"])
    create_audit_log(
        operator_id=current_user["id"],
        action="SUBMISSION_RECEIVED",
        target_type="submission",
        target_id=submission["id"],
        success=True,
        detail={"problem_id": submission["problem_id"]},
    )
    background_tasks.add_task(process_submission, submission["id"])

    return success_response(
        code=202,
        message="submission accepted",
        data={
            "submission_id": submission["id"],
            "status": submission["status"],
        },
    )


@router.get("")
async def list_submissions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    problem_id: str | None = None,
    user_id: str | None = None,
    status: Literal["pending", "running", "finished", "failed"] | None = None,
    result: Literal["AC", "WA", "RE", "TLE", "SE"] | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    current_user=Depends(get_current_user),
):
    own_user_id = None
    requested_user_id = user_id

    if current_user["role"] == "student":
        if user_id is not None and user_id != current_user["id"]:
            raise HTTPException(
                status_code=403,
                detail="students can only view their own submissions",
            )
        own_user_id = current_user["id"]
        requested_user_id = None

    submissions, total = get_submissions_paginated(
        page=page,
        page_size=page_size,
        current_user_id=own_user_id,
        problem_id=problem_id,
        user_id=requested_user_id,
        status=status,
        result=result,
        start_time=to_utc_iso(start_time),
        end_time=to_utc_iso(end_time),
    )
    return success_response(
        data={
            "items": [serialize_submission(item) for item in submissions],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("/{submission_id}/rejudge", status_code=202)
async def rejudge_submission(
    submission_id: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(require_teacher),
):
    submission = reset_submission_for_rejudge(submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="submission not found")
    if submission is False:
        raise HTTPException(
            status_code=409,
            detail="only finished or failed submissions can be rejudged",
        )

    create_audit_log(
        operator_id=current_user["id"],
        action="REJUDGE_SUBMISSION",
        target_type="submission",
        target_id=submission_id,
        success=True,
        detail={
            "problem_id": submission["problem_id"],
            "rejudge_requested_at": submission["created_at"],
        },
    )
    background_tasks.add_task(process_submission, submission_id)

    return success_response(
        code=202,
        message="submission accepted for rejudging",
        data={
            "submission_id": submission_id,
            "status": "pending",
        },
    )


@router.get("/{submission_id}")
async def get_submission_detail(
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

    # Test-case data is intentionally available only from the dedicated log
    # endpoint, where role-specific redaction and full-log access auditing occur.
    return success_response(
        data=serialize_submission(submission, include_source=True)
    )
