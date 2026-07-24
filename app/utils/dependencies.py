from fastapi import Depends, HTTPException, Request

from app.repositories.users import get_user_by_id


def get_current_user(request: Request):
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
    return user


def require_teacher(user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="access not allowed")
    return user


def require_admin(user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="access not allowed")
    return user
