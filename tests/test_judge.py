from pathlib import Path

from app.config import TEMP_DIR
from app.judge.comparator import outputs_match
from app.judge.evaluator import judge_submission
from app.judge.runner import run_python_code


def cases():
    return [
        {
            "case_id": "c1",
            "input_data": "1 2\n",
            "expected_output": "3\n",
            "score": 100,
            "is_hidden": 0,
        }
    ]


def test_output_normalization():
    assert outputs_match("3   \r\n\r\n", "3\n")
    assert not outputs_match(" 3\n", "3\n")
    assert not outputs_match("answer: 3\n", "3\n")


def test_ac_wa_re_and_tle():
    assert judge_submission(
        "a,b=map(int,input().split())\nprint(a+b)", cases(), 1.5
    )["result"] == "AC"
    assert judge_submission("print(0)", cases(), 1.5)["result"] == "WA"
    assert judge_submission("print(1/0)", cases(), 1.5)["result"] == "RE"
    assert judge_submission("while True: pass", cases(), 0.1)["result"] == "TLE"


def test_non_utf8_output_is_re_and_temp_is_cleaned():
    before = set(Path(TEMP_DIR).iterdir())
    result = run_python_code(
        "import sys\nsys.stdout.buffer.write(b'\\xff')",
        "",
        1.5,
    )
    after = set(Path(TEMP_DIR).iterdir())
    assert result["status"] == "decode_error"
    assert "UTF-8" in result["message"]
    assert before == after
