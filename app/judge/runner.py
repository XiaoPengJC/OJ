import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from app.config import TEMP_DIR
from app.utils.logs import sanitize_error_message, truncate_text


def _decode_utf8(data: bytes, stream_name: str) -> tuple[str, str | None]:
    try:
        return data.decode("utf-8"), None
    except UnicodeDecodeError:
        message = (
            f"{stream_name} could not be decoded as UTF-8; "
            "the current test case is treated as a runtime error"
        )
        return "", message


def run_python_code(
    source_code: str,
    input_data: str,
    time_limit: float,
) -> dict:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        dir=TEMP_DIR,
        prefix="submission_",
    ) as temp_dir:
        source_path = Path(temp_dir) / "main.py"
        source_path.write_text(source_code, encoding="utf-8")
        start_time = time.perf_counter()

        # Do not inherit the web server's environment. The absolute interpreter
        # path is already known, so PATH and server secrets are unnecessary.
        safe_environment = {
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUNBUFFERED": "1",
        }
        if os.name == "nt":
            # Python on Windows can need SystemRoot to start correctly.
            system_root = os.environ.get("SystemRoot")
            if system_root:
                safe_environment["SystemRoot"] = system_root

        try:
            result = subprocess.run(
                [sys.executable, "-I", str(source_path)],
                input=input_data.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=time_limit,
                cwd=temp_dir,
                env=safe_environment,
                text=False,
                check=False,
                start_new_session=True,
            )
            execution_time = time.perf_counter() - start_time

            stdout, stdout_error = _decode_utf8(result.stdout, "stdout")
            stderr, stderr_error = _decode_utf8(result.stderr, "stderr")
            decode_error = stdout_error or stderr_error

            if decode_error is not None:
                return {
                    "status": "decode_error",
                    "stdout": "",
                    "stderr": truncate_text(decode_error),
                    "execution_time": execution_time,
                    "return_code": result.returncode,
                    "message": decode_error,
                }

            return {
                "status": "finished",
                "stdout": stdout,
                "stderr": sanitize_error_message(stderr),
                "execution_time": execution_time,
                "return_code": result.returncode,
                "message": "",
            }

        except subprocess.TimeoutExpired as error:
            execution_time = time.perf_counter() - start_time
            stdout_bytes = error.stdout or b""
            stderr_bytes = error.stderr or b""
            if isinstance(stdout_bytes, str):
                stdout_bytes = stdout_bytes.encode("utf-8", errors="replace")
            if isinstance(stderr_bytes, str):
                stderr_bytes = stderr_bytes.encode("utf-8", errors="replace")

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            return {
                "status": "timeout",
                "stdout": stdout,
                "stderr": sanitize_error_message(stderr),
                "execution_time": execution_time,
                "return_code": None,
                "message": "time limit exceeded",
            }

        except Exception as error:
            execution_time = time.perf_counter() - start_time
            message = sanitize_error_message(
                f"judge runner failed: {type(error).__name__}: {error}"
            )
            return {
                "status": "system_error",
                "stdout": "",
                "stderr": message,
                "execution_time": execution_time,
                "return_code": None,
                "message": message,
            }
