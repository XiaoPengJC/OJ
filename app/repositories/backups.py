import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import (
    BACKUP_DIR,
    BACKUP_FORMAT_VERSION,
    DATABASE_PATH,
)
from app.repositories.database import get_connection
from app.utils.time import utc_now


def _database_sidecars(database_path: Path) -> tuple[Path, Path]:
    return (
        Path(str(database_path) + "-wal"),
        Path(str(database_path) + "-shm"),
    )


def _remove_database_sidecars(database_path: Path) -> None:
    for sidecar in _database_sidecars(database_path):
        if sidecar.exists():
            sidecar.unlink()


def _checkpoint_database(database_path: Path) -> None:
    connection = sqlite3.connect(database_path, timeout=30)
    try:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        connection.close()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _insert_backup_record(
    backup_id: str,
    backup_path: Path,
    created_at: str,
) -> None:
    connection = get_connection()
    try:
        connection.execute(
            "INSERT INTO backups (id, path, created_at) VALUES (?, ?, ?)",
            (backup_id, str(backup_path), created_at),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _delete_backup_record(backup_id: str) -> None:
    connection = get_connection()
    try:
        connection.execute("DELETE FROM backups WHERE id = ?", (backup_id,))
        connection.commit()
    finally:
        connection.close()


def create_backup():
    backup_id = str(uuid4())
    created_at = utc_now()
    filename_time = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"oj_backup_{filename_time}_{backup_id}.zip"

    # Insert first so the database snapshot contains its own backup record.
    _insert_backup_record(backup_id, backup_path, created_at)

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            database_copy = temp_path / "oj.db"
            manifest_path = temp_path / "manifest.json"

            source = sqlite3.connect(DATABASE_PATH, timeout=30)
            destination = sqlite3.connect(database_copy)
            try:
                source.backup(destination)
            finally:
                destination.close()
                source.close()

            manifest = {
                "backup_id": backup_id,
                "created_at": created_at,
                "storage_type": "sqlite",
                "format_version": BACKUP_FORMAT_VERSION,
                "files": [
                    {
                        "name": "oj.db",
                        "sha256": _sha256(database_copy),
                    }
                ],
            }
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            with zipfile.ZipFile(
                backup_path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive:
                archive.write(database_copy, arcname="oj.db")
                archive.write(manifest_path, arcname="manifest.json")

    except Exception:
        _delete_backup_record(backup_id)
        if backup_path.exists():
            backup_path.unlink()
        raise

    return {
        "backup_id": backup_id,
        "created_at": created_at,
    }


def get_all_backups():
    connection = get_connection()
    try:
        return connection.execute(
            "SELECT * FROM backups ORDER BY created_at DESC"
        ).fetchall()
    finally:
        connection.close()


def get_backup_by_id(backup_id: str):
    connection = get_connection()
    try:
        return connection.execute(
            "SELECT * FROM backups WHERE id = ?",
            (backup_id,),
        ).fetchone()
    finally:
        connection.close()


def validate_database(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    try:
        result = connection.execute("PRAGMA integrity_check").fetchone()
        if result is None or result[0] != "ok":
            raise ValueError("backup database failed integrity check")

        required_tables = {
            "users",
            "problems",
            "test_cases",
            "submissions",
            "judge_logs",
            "audit_logs",
            "backups",
        }
        existing_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        missing = required_tables - existing_tables
        if missing:
            raise ValueError(
                "backup database is missing required tables: "
                + ", ".join(sorted(missing))
            )
    finally:
        connection.close()


def _load_and_validate_archive(
    backup_path: Path,
    backup_id: str,
    temp_path: Path,
) -> Path:
    try:
        with zipfile.ZipFile(backup_path, mode="r") as archive:
            names = set(archive.namelist())
            if names != {"manifest.json", "oj.db"}:
                raise ValueError("backup archive contains an invalid file list")

            manifest_bytes = archive.read("manifest.json")
            database_bytes = archive.read("oj.db")
    except zipfile.BadZipFile as error:
        raise ValueError("invalid backup archive") from error
    except KeyError as error:
        raise ValueError("backup archive is missing required files") from error

    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid backup manifest") from error

    if manifest.get("backup_id") != backup_id:
        raise ValueError("backup manifest ID does not match")
    if manifest.get("storage_type") != "sqlite":
        raise ValueError("unsupported backup storage type")
    if manifest.get("format_version") != BACKUP_FORMAT_VERSION:
        raise ValueError("unsupported backup format")

    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != 1:
        raise ValueError("invalid backup manifest file list")
    file_record = files[0]
    if not isinstance(file_record, dict) or file_record.get("name") != "oj.db":
        raise ValueError("backup manifest does not describe oj.db")

    candidate_database = temp_path / "oj.db"
    candidate_database.write_bytes(database_bytes)
    if file_record.get("sha256") != _sha256(candidate_database):
        raise ValueError("backup database checksum does not match")

    validate_database(candidate_database)
    return candidate_database


def restore_backup(backup_id: str):
    backup = get_backup_by_id(backup_id)
    if backup is None:
        return None

    backup_path = Path(backup["path"])
    if not backup_path.exists():
        raise FileNotFoundError("backup file not found")

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    rollback_path = DATABASE_PATH.with_name(
        f"{DATABASE_PATH.name}.{uuid4().hex}.rollback"
    )
    replacement_path = DATABASE_PATH.with_name(
        f"{DATABASE_PATH.name}.{uuid4().hex}.restore"
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        candidate_database = _load_and_validate_archive(
            backup_path,
            backup_id,
            Path(temp_dir),
        )

        _checkpoint_database(DATABASE_PATH)
        shutil.copy2(DATABASE_PATH, rollback_path)
        try:
            shutil.copy2(candidate_database, replacement_path)
            _remove_database_sidecars(DATABASE_PATH)
            os.replace(replacement_path, DATABASE_PATH)
            _remove_database_sidecars(DATABASE_PATH)
            validate_database(DATABASE_PATH)
        except Exception:
            _remove_database_sidecars(DATABASE_PATH)
            shutil.copy2(rollback_path, DATABASE_PATH)
            _remove_database_sidecars(DATABASE_PATH)
            validate_database(DATABASE_PATH)
            raise
        finally:
            if replacement_path.exists():
                replacement_path.unlink()
            if rollback_path.exists():
                rollback_path.unlink()

    return {
        "backup_id": backup["id"],
        "created_at": backup["created_at"],
    }
