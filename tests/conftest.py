import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_ROOT = Path(__file__).resolve().parent / ".runtime"
os.environ["OJ_PROJECT_ROOT"] = str(TEST_ROOT)
os.environ["OJ_DATABASE_PATH"] = str(TEST_ROOT / "data" / "oj.db")
os.environ["OJ_BACKUP_DIR"] = str(TEST_ROOT / "data" / "backups")
os.environ["OJ_TEMP_DIR"] = str(TEST_ROOT / "temp")
os.environ["OJ_SESSION_SECRET"] = "pytest-session-secret"
os.environ["OJ_ADMIN_USERNAME"] = "admin"
os.environ["OJ_ADMIN_PASSWORD"] = "admin12345"

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    if TEST_ROOT.exists():
        shutil.rmtree(TEST_ROOT)
    (TEST_ROOT / "data" / "backups").mkdir(parents=True)
    (TEST_ROOT / "temp").mkdir(parents=True)

    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, username: str, password: str):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )


def login_admin(client: TestClient):
    response = login(client, "admin", "admin12345")
    assert response.status_code == 200
    return response


def sample_problem(problem_id: str = "P1001", time_limit: float = 1.5):
    return {
        "id": problem_id,
        "title": "A+B Problem",
        "description": "输入两个整数并输出它们的和。",
        "input_description": "一行两个整数。",
        "output_description": "输出两数之和。",
        "samples": [{"input": "1 2\n", "output": "3\n"}],
        "constraints": "|a|, |b| <= 10^9",
        "time_limit": time_limit,
        "memory_limit": 128,
        "difficulty": "easy",
        "tags": ["基础", "输入输出"],
        "test_cases": [
            {
                "case_id": "public_case",
                "input": "1 2\n",
                "output": "3\n",
                "score": 50,
                "is_hidden": False,
            },
            {
                "case_id": "hidden_case",
                "input": "-1 2\n",
                "output": "1\n",
                "score": 50,
                "is_hidden": True,
            },
        ],
    }


def create_problem(client: TestClient, problem_id: str = "P1001", time_limit: float = 1.5):
    response = client.post(
        "/api/problems",
        json=sample_problem(problem_id, time_limit),
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def create_user(
    client: TestClient,
    username: str,
    role: str = "student",
    password: str = "password123",
):
    response = client.post(
        "/api/users",
        json={"username": username, "password": password, "role": role},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]
