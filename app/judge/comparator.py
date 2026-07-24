def normalize_output(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split(sep='\n')
    lines = [line.rstrip(" \t") for line in lines]

    while lines and lines[-1] == "":
        lines.pop()

    result = '\n'.join(lines)

    return result

def outputs_match(actual: str, expected: str) -> bool:
    return normalize_output(actual) == normalize_output(expected)
