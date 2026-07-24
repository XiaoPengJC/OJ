import os
from pathlib import Path

DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = Path(
    os.getenv("OJ_PROJECT_ROOT", str(DEFAULT_PROJECT_ROOT))
).resolve()

DATABASE_PATH = Path(
    os.getenv("OJ_DATABASE_PATH", str(PROJECT_ROOT / "data" / "oj.db"))
).resolve()
BACKUP_DIR = Path(
    os.getenv("OJ_BACKUP_DIR", str(PROJECT_ROOT / "data" / "backups"))
).resolve()
TEMP_DIR = Path(
    os.getenv("OJ_TEMP_DIR", str(PROJECT_ROOT / "temp"))
).resolve()

SESSION_SECRET = os.getenv(
    "OJ_SESSION_SECRET",
    "development-only-change-me-before-deployment",
)

MAX_SOURCE_SIZE = 64 * 1024
MAX_LOG_LENGTH = 4000
BACKUP_FORMAT_VERSION = 1

DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
