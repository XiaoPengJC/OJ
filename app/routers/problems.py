import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.models.problem import ProblemCreateRequest
from app.repositories.audit_logs import create_audit_log
from app.repositories.problems import (
    create_problem,
    delete_problem,
    get_all_problems,
    get_problem_by_id,
    get_test_cases_by_problem_id,
    update_problem,
)
from app.utils.dependencies import get_current_user, require_teacher
from app.utils.responses import success_response

router = APIRouter(prefix="/api/problems", tags=["problems"])


def serialize_problem(problem, include_test_cases: bool = False) -> dict:
    data = {
        "id": problem["id"],
        "title": problem["title"],
        "description": problem["description"],
        "input_description": problem["input_description"],
        "output_description": problem["output_description"],
        "samples": json.loads(problem["samples"]),
        "constraints": problem["constraints_text"],
        "time_limit": problem["time_limit"],
        "memory_limit": problem["memory_limit"],
        "difficulty": problem["difficulty"],
        "tags": json.loads(problem["tags"]),
        "created_at": problem["created_at"],
        "updated_at": problem["updated_at"],
    }
    if include_test_cases:
        data["test_cases"] = [
            {
                "case_id": test_case["case_id"],
                "input": test_case["input_data"],
                "output": test_case["expected_output"],
                "score": test_case["score"],
                "is_hidden": bool(test_case["is_hidden"]),
            }
            for test_case in get_test_cases_by_problem_id(problem["id"])
        ]
    return data


@router.post("", status_code=201)
async def create_problem_route(
    data: ProblemCreateRequest,
    current_user=Depends(require_teacher),
):
    if get_problem_by_id(data.id) is not None:
        raise HTTPException(status_code=409, detail="problem already exists")

    try:
        problem = create_problem(data)
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail="problem already exists",
        ) from error

    create_audit_log(
        operator_id=current_user["id"],
        action="CREATE_PROBLEM",
        target_type="problem",
        target_id=problem["id"],
        success=True,
        detail={"title": problem["title"]},
    )
    return success_response(
        code=201,
        message="problem created",
        data=serialize_problem(problem, include_test_cases=True),
    )


@router.get("")
async def list_problems(current_user=Depends(get_current_user)):
    problems = get_all_problems()
    return success_response(
        data=[
            {
                "id": problem["id"],
                "title": problem["title"],
                "difficulty": problem["difficulty"],
                "tags": json.loads(problem["tags"]),
                "time_limit": problem["time_limit"],
                "memory_limit": problem["memory_limit"],
            }
            for problem in problems
        ]
    )


@router.get("/{problem_id}")
async def get_problem_detail(
    problem_id: str,
    current_user=Depends(get_current_user),
):
    problem = get_problem_by_id(problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="problem not found")
    return success_response(
        data=serialize_problem(
            problem,
            include_test_cases=current_user["role"] in ("teacher", "admin"),
        )
    )


@router.put("/{problem_id}")
async def update_problem_route(
    problem_id: str,
    data: ProblemCreateRequest,
    current_user=Depends(require_teacher),
):
    if data.id != problem_id:
        raise HTTPException(
            status_code=400,
            detail="problem id cannot be changed",
        )

    problem = update_problem(problem_id, data)
    if problem is None:
        raise HTTPException(status_code=404, detail="problem not found")

    create_audit_log(
        operator_id=current_user["id"],
        action="UPDATE_PROBLEM",
        target_type="problem",
        target_id=problem_id,
        success=True,
        detail={"title": problem["title"]},
    )
    return success_response(
        message="problem updated",
        data=serialize_problem(problem, include_test_cases=True),
    )


@router.delete("/{problem_id}")
async def delete_problem_route(
    problem_id: str,
    current_user=Depends(require_teacher),
):
    if not delete_problem(problem_id):
        raise HTTPException(status_code=404, detail="problem not found")

    create_audit_log(
        operator_id=current_user["id"],
        action="DELETE_PROBLEM",
        target_type="problem",
        target_id=problem_id,
        success=True,
    )
    return success_response(
        message="problem deleted",
        data={"id": problem_id},
    )
