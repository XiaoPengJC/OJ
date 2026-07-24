import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.user_management import UserCreateRequest, UserUpdateRequest
from app.repositories.audit_logs import create_audit_log
from app.repositories.users import (
    create_user_with_role,
    get_user_by_id,
    get_user_by_username,
    get_users_paginated,
    update_user,
)
from app.utils.dependencies import require_admin
from app.utils.responses import success_response
from app.utils.security import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


def serialize_user(user) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "is_active": bool(user["is_active"]),
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
    }


@router.get("")
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_admin),
):
    users, total = get_users_paginated(page, page_size)
    return success_response(
        data={
            "items": [serialize_user(user) for user in users],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("", status_code=201)
async def create_user_route(
    data: UserCreateRequest,
    current_user=Depends(require_admin),
):
    if get_user_by_username(data.username) is not None:
        raise HTTPException(status_code=409, detail="username already exists")

    try:
        user = create_user_with_role(
            data.username,
            hash_password(data.password),
            data.role,
        )
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail="username already exists",
        ) from error

    create_audit_log(
        operator_id=current_user["id"],
        action="CREATE_USER",
        target_type="user",
        target_id=user["id"],
        success=True,
        detail={"username": user["username"], "role": user["role"]},
    )
    return success_response(
        code=201,
        message="user created",
        data=serialize_user(user),
    )


@router.get("/{user_id}")
async def get_user_detail(
    user_id: str,
    current_user=Depends(require_admin),
):
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return success_response(data=serialize_user(user))


@router.put("/{user_id}")
async def update_user_route(
    user_id: str,
    data: UserUpdateRequest,
    current_user=Depends(require_admin),
):
    if user_id == current_user["id"] and data.is_active is False:
        raise HTTPException(
            status_code=400,
            detail="cannot deactivate your own account",
        )

    original_user = get_user_by_id(user_id)
    if original_user is None:
        raise HTTPException(status_code=404, detail="user not found")

    user = update_user(user_id, data.role, data.is_active)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    if data.role is not None and data.role != original_user["role"]:
        create_audit_log(
            operator_id=current_user["id"],
            action="UPDATE_USER_ROLE",
            target_type="user",
            target_id=user["id"],
            success=True,
            detail={
                "old_role": original_user["role"],
                "new_role": user["role"],
            },
        )

    if data.is_active is False and bool(original_user["is_active"]):
        create_audit_log(
            operator_id=current_user["id"],
            action="DISABLE_USER",
            target_type="user",
            target_id=user["id"],
            success=True,
            detail={"username": user["username"]},
        )
    elif data.is_active is True and not bool(original_user["is_active"]):
        create_audit_log(
            operator_id=current_user["id"],
            action="ENABLE_USER",
            target_type="user",
            target_id=user["id"],
            success=True,
            detail={"username": user["username"]},
        )

    return success_response(message="user updated", data=serialize_user(user))
