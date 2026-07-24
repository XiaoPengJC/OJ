from .conftest import create_user, login, login_admin


def test_registration_login_logout_and_duplicate(client):
    response = client.post(
        "/api/auth/register",
        json={"username": "student01", "password": "password123"},
    )
    assert response.status_code == 201
    assert response.json()["data"]["role"] == "student"
    assert "password" not in response.text

    duplicate = client.post(
        "/api/auth/register",
        json={"username": "student01", "password": "password123"},
    )
    assert duplicate.status_code == 409
    assert login(client, "student01", "wrongpass").status_code == 401
    assert login(client, "student01", "password123").status_code == 200
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_user_permissions_pagination_and_disable(client):
    login_admin(client)
    teacher = create_user(client, "teacher01", "teacher")
    student = create_user(client, "student01", "student")

    listing = client.get("/api/users?page=1&page_size=1")
    assert listing.status_code == 200
    assert set(listing.json()["data"]) == {"items", "total", "page", "page_size"}
    assert listing.json()["data"]["page_size"] == 1
    assert client.get(f"/api/users/{student['id']}").status_code == 200

    update = client.put(
        f"/api/users/{student['id']}",
        json={"role": "teacher", "is_active": False},
    )
    assert update.status_code == 200
    assert update.json()["data"]["role"] == "teacher"
    assert update.json()["data"]["is_active"] is False

    client.post("/api/auth/logout")
    assert login(client, "student01", "password123").status_code == 403
    assert login(client, "teacher01", "password123").status_code == 200
    assert client.get("/api/users").status_code == 403


def test_admin_cannot_disable_self(client):
    login_admin(client)
    admin_id = client.get("/api/auth/me").json()["data"]["id"]
    response = client.put(
        f"/api/users/{admin_id}",
        json={"is_active": False},
    )
    assert response.status_code == 400
