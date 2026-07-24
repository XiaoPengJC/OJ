from app.utils.logs import (
    sanitize_error_message,
    sanitize_student_stderr,
    truncate_text,
)


def to_student_log_view(log) -> dict:
    data = {
        "id": log["id"],
        "submission_id": log["submission_id"],
        "case_id": log["case_id"],
        "result": log["result"],
        "score": log["score"],
        "time_used": log["time_used"],
        "message": truncate_text(sanitize_error_message(log["message"])),
        "stderr": sanitize_student_stderr(log["stderr"]),
        "created_at": log["created_at"],
    }

    if not bool(log["is_hidden"]):
        data["stdout"] = truncate_text(log["stdout"])
        data["expected_output"] = truncate_text(log["expected_output"])

    return data


def to_teacher_log_view(log) -> dict:
    return {
        "id": log["id"],
        "submission_id": log["submission_id"],
        "case_id": log["case_id"],
        "result": log["result"],
        "score": log["score"],
        "time_used": log["time_used"],
        "memory_used": log["memory_used"],
        "exit_code": log["exit_code"],
        "input_data": truncate_text(log["input_data"]),
        "stdout": truncate_text(log["stdout"]),
        "stderr": truncate_text(sanitize_error_message(log["stderr"])),
        "expected_output": truncate_text(log["expected_output"]),
        "message": truncate_text(sanitize_error_message(log["message"])),
        "is_hidden": bool(log["is_hidden"]),
        "created_at": log["created_at"],
    }
