from app.repositories.submissions import (
    create_submission,
    mark_submission_finished,
    reset_submission_for_rejudge,
)
from app.models.submission import SubmissionCreateRequest
from app.utils.logs import MAX_LOG_LENGTH, sanitize_error_message, truncate_text

from .conftest import create_problem, create_user, login, login_admin


def submit(client, code):
    response = client.post(
        "/api/submissions",
        json={"problem_id": "P1001", "language": "python", "source_code": code},
    )
    assert response.status_code == 202, response.text
    return response.json()["data"]["submission_id"]


def test_submission_ownership_hidden_logs_filters_and_rejudge(client):
    login_admin(client)
    create_problem(client)
    first = create_user(client, "student01")
    create_user(client, "student02")

    client.post("/api/auth/logout")
    login(client, "student01", "password123")
    submission_id = submit(client, "a,b=map(int,input().split())\nprint(a+b)")
    detail = client.get(f"/api/submissions/{submission_id}").json()["data"]
    assert detail["status"] == "finished"
    assert "case_results" not in detail

    logs = client.get(f"/api/submissions/{submission_id}/logs").json()["data"]
    public_log = next(item for item in logs if item["case_id"] == "public_case")
    hidden_log = next(item for item in logs if item["case_id"] == "hidden_case")
    assert "stdout" in public_log and "expected_output" in public_log
    assert "stdout" not in hidden_log
    assert "expected_output" not in hidden_log
    assert "input_data" not in hidden_log

    client.post("/api/auth/logout")
    login(client, "student02", "password123")
    assert client.get(f"/api/submissions/{submission_id}").status_code == 403
    assert client.get(f"/api/submissions/{submission_id}/logs").status_code == 403
    assert client.get(f"/api/submissions?user_id={first['id']}").status_code == 403

    client.post("/api/auth/logout")
    login_admin(client)
    query = client.get(f"/api/submissions?problem_id=P1001&user_id={first['id']}&result=AC")
    assert query.status_code == 200
    assert query.json()["data"]["total"] == 1
    full_logs = client.get(f"/api/submissions/{submission_id}/logs")
    assert "input_data" in full_logs.json()["data"][1]
    assert client.get(f"/api/logs?problem_id=P1001&user_id={first['id']}").status_code == 200

    rejudge = client.post(f"/api/submissions/{submission_id}/rejudge")
    assert rejudge.status_code == 202
    assert client.get(f"/api/submissions/{submission_id}").json()["data"]["result"] == "AC"
    audits = client.get("/api/audit-logs?action=REJUDGE_SUBMISSION").json()["data"]
    assert audits["total"] == 1


def test_illegal_state_transitions(client):
    login_admin(client)
    create_problem(client)
    user = create_user(client, "student01")
    data = SubmissionCreateRequest(
        problem_id="P1001",
        language="python",
        source_code="print(3)",
    )
    submission = create_submission(data, user["id"])
    assert mark_submission_finished(submission["id"], "AC", 100, 0.1) is False
    assert reset_submission_for_rejudge(submission["id"]) is False


def test_log_sanitization_and_truncation():
    unix = sanitize_error_message('/mnt/data/secret/submission/main.py", line 3')
    windows = sanitize_error_message(r'C:\\oj\\temp\\abc\\main.py", line 3')
    assert "/mnt/data" not in unix
    assert "C:\\oj" not in windows
    text = truncate_text("x" * (MAX_LOG_LENGTH + 500))
    assert len(text) == MAX_LOG_LENGTH
    assert text.endswith("...[truncated]")


def test_system_error_creates_failed_submission_and_log(client, monkeypatch):
    login_admin(client)
    create_problem(client)
    create_user(client, "student01")
    client.post("/api/auth/logout")
    login(client, "student01", "password123")

    def explode(*args, **kwargs):
        raise RuntimeError("forced evaluator failure")

    monkeypatch.setattr("app.services.judge_service.judge_submission", explode)
    submission_id = submit(client, "print(3)")
    detail = client.get(f"/api/submissions/{submission_id}").json()["data"]
    assert detail["status"] == "failed"
    assert detail["result"] == "SE"
    logs = client.get(f"/api/submissions/{submission_id}/logs").json()["data"]
    assert logs[0]["result"] == "SE"


def test_submission_validation_teacher_permissions_and_full_log_audit(client):
    login_admin(client)
    create_problem(client)
    create_user(client, "teacher01", "teacher")
    create_user(client, "student01", "student")

    client.post("/api/auth/logout")
    login(client, "student01", "password123")
    assert client.post(
        "/api/submissions",
        json={"problem_id": "P1001", "language": "python", "source_code": "   "},
    ).status_code == 422
    assert client.post(
        "/api/submissions",
        json={"problem_id": "DOES_NOT_EXIST", "language": "python", "source_code": "print(1)"},
    ).status_code == 404
    submission_id = submit(client, "print(sum(map(int,input().split())))")

    client.post("/api/auth/logout")
    login(client, "teacher01", "password123")
    assert client.get("/api/submissions").status_code == 200
    assert client.get(f"/api/submissions/{submission_id}/logs").status_code == 200
    assert client.get("/api/logs").status_code == 200
    assert client.get("/api/audit-logs").status_code == 403

    client.post("/api/auth/logout")
    login_admin(client)
    audit = client.get("/api/audit-logs?action=VIEW_FULL_JUDGE_LOG").json()["data"]
    assert audit["total"] >= 2
