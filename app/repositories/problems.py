import json

from app.models.problem import ProblemCreateRequest
from app.repositories.database import get_connection
from app.utils.time import utc_now


def get_problem_by_id(problem_id: str):
    connection = get_connection()
    try:
        return connection.execute(
            "SELECT * FROM problems WHERE id = ?",
            (problem_id,),
        ).fetchone()
    finally:
        connection.close()


def create_problem(data: ProblemCreateRequest):
    current_time = utc_now()
    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO problems (
                id, title, description, input_description,
                output_description, samples, constraints_text,
                time_limit, memory_limit, difficulty, tags,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.id,
                data.title,
                data.description,
                data.input_description,
                data.output_description,
                json.dumps(
                    [sample.model_dump() for sample in data.samples],
                    ensure_ascii=False,
                ),
                data.constraints,
                data.time_limit,
                data.memory_limit,
                data.difficulty,
                json.dumps(data.tags, ensure_ascii=False),
                current_time,
                current_time,
            ),
        )

        for test_case in data.test_cases:
            connection.execute(
                """
                INSERT INTO test_cases (
                    problem_id, case_id, input_data,
                    expected_output, score, is_hidden
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    data.id,
                    test_case.case_id,
                    test_case.input,
                    test_case.output,
                    test_case.score,
                    int(test_case.is_hidden),
                ),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return get_problem_by_id(data.id)


def get_all_problems():
    connection = get_connection()
    try:
        return connection.execute(
            "SELECT * FROM problems ORDER BY created_at DESC"
        ).fetchall()
    finally:
        connection.close()


def get_test_cases_by_problem_id(problem_id: str):
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT *
            FROM test_cases
            WHERE problem_id = ?
            ORDER BY id
            """,
            (problem_id,),
        ).fetchall()
    finally:
        connection.close()


def update_problem(problem_id: str, data: ProblemCreateRequest):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE problems
            SET title = ?, description = ?, input_description = ?,
                output_description = ?, samples = ?, constraints_text = ?,
                time_limit = ?, memory_limit = ?, difficulty = ?,
                tags = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                data.title,
                data.description,
                data.input_description,
                data.output_description,
                json.dumps(
                    [sample.model_dump() for sample in data.samples],
                    ensure_ascii=False,
                ),
                data.constraints,
                data.time_limit,
                data.memory_limit,
                data.difficulty,
                json.dumps(data.tags, ensure_ascii=False),
                utc_now(),
                problem_id,
            ),
        )
        if cursor.rowcount == 0:
            connection.rollback()
            return None

        connection.execute(
            "DELETE FROM test_cases WHERE problem_id = ?",
            (problem_id,),
        )
        for test_case in data.test_cases:
            connection.execute(
                """
                INSERT INTO test_cases (
                    problem_id, case_id, input_data,
                    expected_output, score, is_hidden
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    problem_id,
                    test_case.case_id,
                    test_case.input,
                    test_case.output,
                    test_case.score,
                    int(test_case.is_hidden),
                ),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return get_problem_by_id(problem_id)


def delete_problem(problem_id: str) -> bool:
    connection = get_connection()
    try:
        cursor = connection.execute(
            "DELETE FROM problems WHERE id = ?",
            (problem_id,),
        )
        connection.commit()
        return cursor.rowcount == 1
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
