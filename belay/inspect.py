import inspect
import re
from io import StringIO
from tokenize import (
    COMMENT,
    DEDENT,
    INDENT,
    NEWLINE,
    OP,
    STRING,
    generate_tokens,
    untokenize,
)
from typing import Tuple

_pat_no_decorators = re.compile(
    r"^(\s*def\s)|(\s*async\s+def\s)|(.*(?<!\w)lambda(:|\s))"
)


class _NoAction(Exception):
    pass


def _dedent_tokenizer(code):
    indent_to_remove = ""
    for (
        token_type,
        string,
        (start_line, start_col),
        (end_line, end_col),  # noqa: B007
        _,
    ) in generate_tokens(StringIO(code).readline):
        print(f"{token_type=} {string=} {start_line=} {end_line=}")
        if start_line == 1 and start_col == 0:
            # First Token
            if token_type != INDENT:
                # No action to perform
                raise _NoAction
            indent_to_remove = string
        if start_col == 0:
            if token_type == INDENT:
                if not string.startswith(indent_to_remove):
                    raise IndentationError
                string = string[len(indent_to_remove) :]
        yield token_type, string


def _dedent(code):
    try:
        return untokenize(_dedent_tokenizer(code))
    except _NoAction:
        return code


def getsource(f) -> Tuple[str, int, str]:
    """Get source code with mild post processing.

    * strips leading decorators.
    * Trims leading whitespace indent.

    Parameters
    ----------
    f: Callable
        Function to get source code of.

    Returns
    -------
    src_code: str
        Source code. Always ends in a newline.
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

    src_code = "".join(lines)
    src_lineno += offset

    src_code = _dedent(src_code)

    return src_code, src_lineno, src_file
