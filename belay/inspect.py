import inspect
import re
from typing import Tuple

_pat_no_decorators = re.compile(
    r"^(\s*def\s)|(\s*async\s+def\s)|(.*(?<!\w)lambda(:|\s))"
)


def getsource(f) -> Tuple[str, int, str]:
    """Get source code data without decorators.

    Trims leading whitespace and removes decorators.

    Parameters
    ----------
    f: Callable
        Function to get source code of.

    Returns
    -------
    src_code: str
        Source code.
    src_lineno: int
        Line number of code begin.
    src_file: str
        Path to file containing source code.
    """
    src_file = inspect.getsourcefile(f)
    if src_file is None:
        raise Exception(f"Unable to get source file for {f}.")
    lines, src_lineno = inspect.getsourcelines(f)

    offset = 0
    for line in lines:
        if _pat_no_decorators.match(line):
            break
        offset += 1

    lines = lines[offset:]

    # Trim leading whitespace
    n_leading_whitespace = len(lines[0]) - len(lines[0].lstrip())
    lines = [line[n_leading_whitespace:] for line in lines]

    src_code = "".join(lines)
    src_lineno += offset

    return src_code, src_lineno, src_file
