import sqlite3

from fastapi import APIRouter, HTTPException, Request

from app.models.user import UserLoginRequest, UserRegisterRequest
from app.repositories.users import (
    create_user,
    get_user_by_id,
    get_user_by_username,
)
from app.utils.responses import success_response
from app.utils.security import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def serialize_user(user) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "is_active": bool(user["is_active"]),
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
    }


@router.post("/register", status_code=201)
async def register(data: UserRegisterRequest):
    if get_user_by_username(data.username) is not None:
        raise HTTPException(status_code=409, detail="username already exists")

    try:
        user = create_user(data.username, hash_password(data.password))
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail="username already exists",
        ) from error

    return success_response(
        code=201,
        message="user registered",
        data=serialize_user(user),
    )


@router.post("/login")
async def login(data: UserLoginRequest, request: Request):
    user = get_user_by_username(data.username)
    if user is None or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail="invalid username or password",
        )
    if not bool(user["is_active"]):
        raise HTTPException(status_code=403, detail="user not active")

    request.session.clear()
    request.session["user_id"] = user["id"]
    return success_response(
        message="login successful",
        data=serialize_user(user),
    )


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return success_response(message="logout successful", data=None)


@router.get("/me")
async def get_me(request: Request):
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="not logged in")

    user = get_user_by_id(user_id)
    if user is None:
        request.session.clear()
        raise HTTPException(status_code=401, detail="not logged in")
    if not bool(user["is_active"]):
        request.session.clear()
        raise HTTPException(status_code=403, detail="user not active")

    return success_response(data=serialize_user(user))
