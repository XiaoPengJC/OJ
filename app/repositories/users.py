from uuid import uuid4

from app.repositories.database import get_connection
from app.utils.time import utc_now

VALID_ROLES = ("student", "teacher", "admin")


def get_user_by_username(username: str):
    connection = get_connection()
    try:
        return connection.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    finally:
        connection.close()


def get_user_by_id(user_id: str):
    connection = get_connection()
    try:
        return connection.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        connection.close()


def create_user(username: str, password_hash: str):
    return create_user_with_role(username, password_hash, "student")


def create_user_with_role(
    username: str,
    password_hash: str,
    role: str,
):
    if role not in VALID_ROLES:
        raise ValueError("invalid user role")

    user_id = str(uuid4())
    current_time = utc_now()
    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO users (
                id, username, password_hash, role,
                is_active, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 1, ?, ?)
            """,
            (
                user_id,
                username,
                password_hash,
                role,
                current_time,
                current_time,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return get_user_by_id(user_id)


def get_users_paginated(page: int, page_size: int):
    offset = (page - 1) * page_size
    connection = get_connection()

    try:
        total = connection.execute(
            "SELECT COUNT(*) AS count FROM users"
        ).fetchone()["count"]
        users = connection.execute(
            """
            SELECT *
            FROM users
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        ).fetchall()
        return users, total
    finally:
        connection.close()


def update_user(
    user_id: str,
    role: str | None = None,
    is_active: bool | None = None,
):
    updates: list[str] = []
    values: list[object] = []

    if role is not None:
        if role not in VALID_ROLES:
            raise ValueError("invalid user role")
        updates.append("role = ?")
        values.append(role)

    if is_active is not None:
        updates.append("is_active = ?")
        values.append(int(is_active))

    if not updates:
        return get_user_by_id(user_id)

    updates.append("updated_at = ?")
    values.append(utc_now())
    values.append(user_id)

    connection = get_connection()
    try:
        cursor = connection.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            values,
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return get_user_by_id(user_id)
