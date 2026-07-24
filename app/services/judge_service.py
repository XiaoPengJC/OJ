from app.judge.evaluator import judge_submission
from app.repositories.audit_logs import create_audit_log
from app.repositories.problems import (
    get_problem_by_id,
    get_test_cases_by_problem_id,
)
from app.repositories.submissions import (
    get_submission_by_id,
    mark_submission_failed,
    mark_submission_finished,
    mark_submission_running,
    save_judge_logs,
    save_system_error_log,
)
from app.utils.logs import sanitize_error_message


def _system_event(
    action: str,
    submission_id: str,
    success: bool,
    detail: dict | None = None,
) -> None:
    create_audit_log(
        operator_id="system",
        action=action,
        target_type="submission",
        target_id=submission_id,
        success=success,
        detail=detail,
    )


def process_submission(submission_id: str) -> None:
    total_time = 0.0

    try:
        submission = get_submission_by_id(submission_id)
        if submission is None:
            return
        if not mark_submission_running(submission_id):
            return

        _system_event(
            "JUDGING_STARTED",
            submission_id,
            True,
            {"problem_id": submission["problem_id"]},
        )

        problem = get_problem_by_id(submission["problem_id"])
        if problem is None:
            raise RuntimeError("problem configuration no longer exists")

        test_cases = get_test_cases_by_problem_id(submission["problem_id"])
        if not test_cases:
            raise RuntimeError("problem has no test cases")

        judge_result = judge_submission(
            source_code=submission["source_code"],
            test_cases=test_cases,
            time_limit=float(problem["time_limit"]),
        )
        total_time = judge_result["total_time"]
        save_judge_logs(
            submission_id,
            test_cases,
            judge_result["cases"],
        )

        if judge_result["result"] == "SE":
            if not mark_submission_failed(submission_id, total_time):
                raise RuntimeError("could not mark submission as failed")
            _system_event(
                "JUDGING_FAILED",
                submission_id,
                False,
                {"result": "SE", "total_time": total_time},
            )
            return

        if not mark_submission_finished(
            submission_id,
            judge_result["result"],
            judge_result["score"],
            total_time,
        ):
            raise RuntimeError("could not mark submission as finished")

        _system_event(
            "JUDGING_FINISHED",
            submission_id,
            True,
            {
                "result": judge_result["result"],
                "score": judge_result["score"],
                "total_time": total_time,
            },
        )

    except Exception as error:
        message = sanitize_error_message(
            f"evaluation system error: {type(error).__name__}: {error}"
        )
        try:
            save_system_error_log(submission_id, message, total_time)
        finally:
            mark_submission_failed(submission_id, total_time)
            _system_event(
                "JUDGING_FAILED",
                submission_id,
                False,
                {"message": message, "total_time": total_time},
            )
