import os

from app.repositories.users import create_user_with_role, get_user_by_username
from app.utils.security import hash_password

DEFAULT_ADMIN_USERNAME = os.getenv("OJ_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("OJ_ADMIN_PASSWORD", "admin12345")


def ensure_initial_admin() -> None:
    admin = get_user_by_username(DEFAULT_ADMIN_USERNAME)
    if admin is None:
        create_user_with_role(
            DEFAULT_ADMIN_USERNAME,
            hash_password(DEFAULT_ADMIN_PASSWORD),
            "admin",
        )
