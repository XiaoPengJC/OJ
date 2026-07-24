import re

from app.config import MAX_LOG_LENGTH

TRUNCATION_MARKER = "...[truncated]"

# Unix absolute paths, including /mnt, /srv, /workspace, /Users, /home, etc.
_UNIX_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])/(?:[^\s/:\"']+/)+[^\s:\"']*"
)
# Windows absolute paths such as C:\\oj\\temp\\main.py or C:/oj/temp/main.py.
_WINDOWS_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])[A-Za-z]:[\\/](?:[^\s:\"']+[\\/])*[^\s:\"']*"
)


def truncate_text(
    value: str | None,
    max_length: int = MAX_LOG_LENGTH,
) -> str:
    if value is None:
        return ""

    text = str(value)
    if len(text) <= max_length:
        return text

    prefix_length = max(0, max_length - len(TRUNCATION_MARKER))
    return text[:prefix_length] + TRUNCATION_MARKER


def sanitize_error_message(value: str | None) -> str:
    text = str(value or "")
    text = _WINDOWS_PATH_RE.sub("<submission>/main.py", text)
    text = _UNIX_PATH_RE.sub("<submission>/main.py", text)
    return truncate_text(text)


def sanitize_log_text(value: str | None) -> str:
    return sanitize_error_message(value)


def sanitize_student_stderr(stderr: str | None) -> str:
    sanitized = sanitize_error_message(stderr)
    if not sanitized:
        return ""

    lines = [line for line in sanitized.splitlines() if line.strip()]
    has_traceback = any(
        line.startswith("Traceback (most recent call last)") for line in lines
    )
    if not has_traceback:
        return sanitized

    final_line = lines[-1] if lines else "RuntimeError: program exited abnormally"
    return truncate_text(f"运行错误：{final_line}")
