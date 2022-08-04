import inspect
import re

_pat_no_decorators = re.compile(
    r"^(\s*def\s)|(\s*async\s+def\s)|(.*(?<!\w)lambda(:|\s))"
)


def getsource(f):
    """Get source code data without decorators.

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
    lines, src_lineno = inspect.getsourcelines(f)
    src_file = inspect.getsourcefile(f)

    offset = 0
    for line in lines:
        if _pat_no_decorators.match(line):
            break
        offset += 1

    lines = lines[offset:]
    src_code = "".join(lines)
    src_lineno += offset

    return src_code, src_lineno, src_file
