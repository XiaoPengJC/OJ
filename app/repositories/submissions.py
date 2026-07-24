from uuid import uuid4

from app.models.submission import SubmissionCreateRequest
from app.repositories.database import get_connection
from app.utils.logs import sanitize_log_text, truncate_text
from app.utils.time import utc_now

FINISHED_RESULTS = ("AC", "WA", "RE", "TLE")


def create_submission(data: SubmissionCreateRequest, user_id: str):
    submission_id = str(uuid4())
    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO submissions (
                id, user_id, problem_id, language, source_code,
                status, result, score, total_time,
                created_at, started_at, finished_at
            )
            VALUES (?, ?, ?, ?, ?, 'pending', NULL, 0, NULL, ?, NULL, NULL)
            """,
            (
                submission_id,
                user_id,
                data.problem_id,
                data.language,
                data.source_code,
                utc_now(),
            ),
        )
        connection.commit()
        return connection.execute(
            "SELECT * FROM submissions WHERE id = ?",
            (submission_id,),
        ).fetchone()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_submission_by_id(submission_id: str):
    connection = get_connection()
    try:
        return connection.execute(
            "SELECT * FROM submissions WHERE id = ?",
            (submission_id,),
        ).fetchone()
    finally:
        connection.close()


def mark_submission_running(submission_id: str) -> bool:
    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            UPDATE submissions
            SET status = 'running', result = NULL, started_at = ?
            WHERE id = ? AND status = 'pending' AND result IS NULL
            """,
            (utc_now(), submission_id),
        )
        connection.commit()
        return cursor.rowcount == 1
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def mark_submission_finished(
    submission_id: str,
    result: str,
    score: int,
    total_time: float,
) -> bool:
    if result not in FINISHED_RESULTS:
        raise ValueError("invalid finished submission result")

    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            UPDATE submissions
            SET status = 'finished', result = ?, score = ?,
                total_time = ?, finished_at = ?
            WHERE id = ? AND status = 'running' AND result IS NULL
            """,
            (result, score, total_time, utc_now(), submission_id),
        )
        connection.commit()
        return cursor.rowcount == 1
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def mark_submission_failed(
    submission_id: str,
    total_time: float | None = None,
) -> bool:
    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            UPDATE submissions
            SET status = 'failed', result = 'SE', score = 0,
                total_time = ?, finished_at = ?
            WHERE id = ?
              AND status IN ('pending', 'running')
              AND result IS NULL
            """,
            (total_time, utc_now(), submission_id),
        )
        connection.commit()
        return cursor.rowcount == 1
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def delete_judge_logs(submission_id: str) -> None:
    connection = get_connection()
    try:
        connection.execute(
            "DELETE FROM judge_logs WHERE submission_id = ?",
            (submission_id,),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def save_judge_logs(
    submission_id: str,
    test_cases,
    case_results: list[dict],
) -> None:
    test_cases_by_id = {
        test_case["case_id"]: test_case for test_case in test_cases
    }
    connection = get_connection()

    try:
        for case_result in case_results:
            test_case = test_cases_by_id.get(case_result["case_id"])
            if test_case is None:
                raise ValueError("judge result contains an unknown case_id")

            connection.execute(
                """
                INSERT INTO judge_logs (
                    submission_id, case_id, result, score,
                    time_used, memory_used, exit_code,
                    input_data, stdout, stderr, expected_output,
                    message, is_hidden, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    submission_id,
                    case_result["case_id"],
                    case_result["result"],
                    case_result["score"],
                    case_result["time_used"],
                    None,
                    case_result["exit_code"],
                    truncate_text(sanitize_log_text(test_case["input_data"])),
                    truncate_text(sanitize_log_text(case_result.get("stdout"))),
                    truncate_text(sanitize_log_text(case_result.get("stderr"))),
                    truncate_text(
                        sanitize_log_text(test_case["expected_output"])
                    ),
                    truncate_text(sanitize_log_text(case_result.get("message"))),
                    int(bool(test_case["is_hidden"])),
                    utc_now(),
                ),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def save_system_error_log(
    submission_id: str,
    message: str,
    time_used: float = 0.0,
) -> None:
    connection = get_connection()
    try:
        connection.execute(
            """
            INSERT OR REPLACE INTO judge_logs (
                submission_id, case_id, result, score,
                time_used, memory_used, exit_code,
                input_data, stdout, stderr, expected_output,
                message, is_hidden, created_at
            )
            VALUES (?, '__system__', 'SE', 0, ?, NULL, NULL,
                    '', '', ?, '', ?, 1, ?)
            """,
            (
                submission_id,
                max(0.0, time_used),
                truncate_text(sanitize_log_text(message)),
                truncate_text(sanitize_log_text(message)),
                utc_now(),
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_judge_logs_by_submission_id(submission_id: str):
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT *
            FROM judge_logs
            WHERE submission_id = ?
            ORDER BY id
            """,
            (submission_id,),
        ).fetchall()
    finally:
        connection.close()


def get_submissions_paginated(
    page: int,
    page_size: int,
    current_user_id: str | None = None,
    problem_id: str | None = None,
    user_id: str | None = None,
    status: str | None = None,
    result: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
):
    conditions: list[str] = []
    values: list[object] = []

    if current_user_id is not None:
        conditions.append("user_id = ?")
        values.append(current_user_id)
    if user_id is not None:
        conditions.append("user_id = ?")
        values.append(user_id)
    if problem_id is not None:
        conditions.append("problem_id = ?")
        values.append(problem_id)
    if status is not None:
        conditions.append("status = ?")
        values.append(status)
    if result is not None:
        conditions.append("result = ?")
        values.append(result)
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
            f"SELECT COUNT(*) AS count FROM submissions {where_clause}",
            values,
        ).fetchone()["count"]
        submissions = connection.execute(
            f"""
            SELECT *
            FROM submissions
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (*values, page_size, offset),
        ).fetchall()
        return submissions, total
    finally:
        connection.close()


def get_judge_logs_paginated(
    page: int,
    page_size: int,
    submission_id: str | None = None,
    problem_id: str | None = None,
    user_id: str | None = None,
    result: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
):
    conditions: list[str] = []
    values: list[object] = []

    if submission_id is not None:
        conditions.append("jl.submission_id = ?")
        values.append(submission_id)
    if problem_id is not None:
        conditions.append("s.problem_id = ?")
        values.append(problem_id)
    if user_id is not None:
        conditions.append("s.user_id = ?")
        values.append(user_id)
    if result is not None:
        conditions.append("jl.result = ?")
        values.append(result)
    if start_time is not None:
        conditions.append("jl.created_at >= ?")
        values.append(start_time)
    if end_time is not None:
        conditions.append("jl.created_at <= ?")
        values.append(end_time)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    offset = (page - 1) * page_size
    connection = get_connection()

    try:
        total = connection.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM judge_logs AS jl
            JOIN submissions AS s ON s.id = jl.submission_id
            {where_clause}
            """,
            values,
        ).fetchone()["count"]
        logs = connection.execute(
            f"""
            SELECT jl.*, s.problem_id, s.user_id
            FROM judge_logs AS jl
            JOIN submissions AS s ON s.id = jl.submission_id
            {where_clause}
            ORDER BY jl.created_at DESC, jl.id DESC
            LIMIT ? OFFSET ?
            """,
            (*values, page_size, offset),
        ).fetchall()
        return logs, total
    finally:
        connection.close()


def reset_submission_for_rejudge(submission_id: str):
    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")
        submission = connection.execute(
            "SELECT * FROM submissions WHERE id = ?",
            (submission_id,),
        ).fetchone()

        if submission is None:
            connection.rollback()
            return None
        if submission["status"] not in ("finished", "failed"):
            connection.rollback()
            return False

        connection.execute(
            "DELETE FROM judge_logs WHERE submission_id = ?",
            (submission_id,),
        )
        connection.execute(
            """
            UPDATE submissions
            SET status = 'pending', result = NULL, score = 0,
                total_time = NULL, started_at = NULL, finished_at = NULL
            WHERE id = ?
            """,
            (submission_id,),
        )
        connection.commit()
        return get_submission_by_id(submission_id)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
