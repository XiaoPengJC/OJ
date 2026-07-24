from app.judge.comparator import outputs_match
from app.judge.runner import run_python_code


def _case_result_from_run(run_result: dict, expected_output: str) -> tuple[str, str]:
    status = run_result["status"]

    if status == "system_error":
        return "SE", run_result.get("message") or "judge system error"
    if status == "timeout":
        return "TLE", "time limit exceeded"
    if status == "decode_error":
        return "RE", run_result.get("message") or "invalid UTF-8 output"
    if run_result["return_code"] != 0:
        return "RE", "program exited abnormally"
    if outputs_match(run_result["stdout"], expected_output):
        return "AC", "accepted"
    return "WA", "output does not match expected answer"


def determine_final_result(case_results: list[dict]) -> str:
    results = [case["result"] for case in case_results]
    if results and all(result == "AC" for result in results):
        return "AC"
    if "SE" in results:
        return "SE"
    if "TLE" in results:
        return "TLE"
    if "RE" in results:
        return "RE"
    return "WA"


def judge_submission(
    source_code: str,
    test_cases,
    time_limit: float,
) -> dict:
    case_results: list[dict] = []
    total_score = 0
    total_time = 0.0

    for test_case in test_cases:
        run_result = run_python_code(
            source_code=source_code,
            input_data=test_case["input_data"],
            time_limit=time_limit,
        )
        case_result, message = _case_result_from_run(
            run_result,
            test_case["expected_output"],
        )
        case_score = test_case["score"] if case_result == "AC" else 0
        total_score += case_score
        total_time += run_result["execution_time"]

        case_results.append(
            {
                "case_id": test_case["case_id"],
                "result": case_result,
                "score": case_score,
                "time_used": run_result["execution_time"],
                "exit_code": run_result["return_code"],
                "stdout": run_result["stdout"],
                "stderr": run_result["stderr"],
                "message": message,
            }
        )

        # The project consistently stops after the first execution-level error.
        if case_result in ("TLE", "RE", "SE"):
            break

    return {
        "result": determine_final_result(case_results),
        "score": total_score,
        "total_time": total_time,
        "cases": case_results,
    }
