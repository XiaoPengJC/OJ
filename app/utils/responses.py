from typing import Any


def success_response(
    data: Any = None,
    message: str = "ok",
    code: int = 200,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "data": data,
    }


def error_response(
    code: int,
    message: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "data": None,
    }

