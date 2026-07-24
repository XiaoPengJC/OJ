import json
from uuid import uuid4

from app.repositories.database import get_connection
from app.utils.time import utc_now


def create_audit_log(
    operator_id: str,
    action: str,
    target_type: str,
    target_id: str,
    success: bool,
    detail: dict | None = None,
):
    connection = get_connection()
    log_id = str(uuid4())

    try:
        connection.execute(
            """
            INSERT INTO audit_logs (
                id, operator_id, action, target_type,
                target_id, success, detail, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id,
                operator_id,
                action,
                target_type,
                target_id,
                int(success),
                json.dumps(detail, ensure_ascii=False)
                if detail is not None
                else None,
                utc_now(),
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return log_id


def get_audit_logs_paginated(
    page: int,
    page_size: int,
    operator_id: str | None = None,
    action: str | None = None,
    target_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
):
    conditions: list[str] = []
    values: list[object] = []

    if operator_id is not None:
        conditions.append("operator_id = ?")
        values.append(operator_id)
    if action is not None:
        conditions.append("action = ?")
        values.append(action)
    if target_id is not None:
        conditions.append("target_id = ?")
        values.append(target_id)
    if start_time is not None:
        conditions.append("created_at >= ?")
        values.append(start_time)
    if end_time is not None:
        conditions.append("created_at <= ?")
        values.append(end_time)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    offset = (page - 1) * page_size
    connection = get_connection()

    try:
        total = connection.execute(
            f"SELECT COUNT(*) AS count FROM audit_logs {where_clause}",
            values,
        ).fetchone()["count"]
        logs = connection.execute(
            f"""
            SELECT *
            FROM audit_logs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (*values, page_size, offset),
        ).fetchall()
        return logs, total
    finally:
        connection.close()
