from .conftest import create_problem, create_user, login, login_admin, sample_problem


def test_problem_crud_validation_and_hidden_permissions(client):
    login_admin(client)
    create_problem(client)
    assert client.post("/api/problems", json=sample_problem()).status_code == 409

    invalid = sample_problem("P_BAD")
    invalid["test_cases"][0]["score"] = 40
    assert client.post("/api/problems", json=invalid).status_code == 422

    detail = client.get("/api/problems/P1001")
    assert detail.status_code == 200
    assert "test_cases" in detail.json()["data"]

    updated = sample_problem()
    updated["title"] = "Updated A+B"
    assert client.put("/api/problems/P1001", json=updated).status_code == 200

    create_user(client, "student01")
    client.post("/api/auth/logout")
    login(client, "student01", "password123")
    student_detail = client.get("/api/problems/P1001")
    assert student_detail.status_code == 200
    assert "test_cases" not in student_detail.json()["data"]
    assert client.post("/api/problems", json=sample_problem("P2")).status_code == 403


def test_deleting_problem_preserves_submission_history(client):
    login_admin(client)
    create_problem(client)
    create_user(client, "student01")
    client.post("/api/auth/logout")
    login(client, "student01", "password123")
    response = client.post(
        "/api/submissions",
        json={
            "problem_id": "P1001",
            "language": "python",
            "source_code": "a,b=map(int,input().split())\nprint(a+b)\n",
        },
    )
    submission_id = response.json()["data"]["submission_id"]

    client.post("/api/auth/logout")
    login_admin(client)
    assert client.delete("/api/problems/P1001").status_code == 200
    detail = client.get(f"/api/submissions/{submission_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["problem_id"] == "P1001"
    assert client.get(f"/api/submissions/{submission_id}/logs").status_code == 200
