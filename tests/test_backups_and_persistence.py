import zipfile
from pathlib import Path

from app.config import BACKUP_DIR, DATABASE_PATH
from app.repositories.database import initialize_database

from .conftest import create_problem, create_user, login_admin


def test_persistence_after_reinitialization(client):
    login_admin(client)
    create_problem(client)
    create_user(client, "student01")
    initialize_database()
    assert client.get("/api/problems/P1001").status_code == 200
    assert client.get("/api/users").json()["data"]["total"] == 2


def test_backup_restore_and_corrupt_backup_safety(client):
    login_admin(client)
    create_problem(client)
    student = create_user(client, "student01")

    created = client.post("/api/admin/backups")
    assert created.status_code == 201
    backup_id = created.json()["data"]["backup_id"]
    backup_file = next(Path(BACKUP_DIR).glob(f"*{backup_id}.zip"))
    with zipfile.ZipFile(backup_file) as archive:
        manifest = archive.read("manifest.json").decode("utf-8")
        assert '"storage_type": "sqlite"' in manifest
        assert '"name": "oj.db"' in manifest

    client.put(f"/api/users/{student['id']}", json={"is_active": False})
    restored = client.post(f"/api/admin/backups/{backup_id}/restore")
    assert restored.status_code == 200
    assert client.get("/api/auth/me").status_code == 401

    login_admin(client)
    user = client.get(f"/api/users/{student['id']}").json()["data"]
    assert user["is_active"] is True

    original_size = DATABASE_PATH.stat().st_size
    backup_file.write_bytes(b"not a zip archive")
    failed = client.post(f"/api/admin/backups/{backup_id}/restore")
    assert failed.status_code == 400
    assert DATABASE_PATH.exists()
    assert DATABASE_PATH.stat().st_size == original_size
    assert client.get("/api/problems/P1001").status_code == 200
