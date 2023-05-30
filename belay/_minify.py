import tokenize
from collections import deque
from io import StringIO
from tokenize import COMMENT, DEDENT, INDENT, NEWLINE, OP, STRING

_token_type_line_start = {NEWLINE, DEDENT, INDENT}


def minify(code: str) -> str:
    """Minify python code.

    Naive code minifying that preserves names and linenos. Performs the following:

        * Removes docstrings.

        * Removes comments.

        * Removes unnecessary whitespace.

    Parameters
    ----------
    code: str
        Python code to minify.

    Returns
    -------
    str
        Minified code.
    """
    out = []
    last_lineno = -1
    last_col = 0
    prev_start_line = 0
    level = 0
    global_start_col = 0
    prev_token_types = deque([INDENT], maxlen=2)

    for (
        token_type,
        string,
        (start_line, start_col),
        (end_line, end_col),
        _,
    ) in tokenize.generate_tokens(StringIO(code).readline):
        prev_token_types.append(token_type)
        prev_token_type = prev_token_types.popleft()

        if start_line > last_lineno:
            last_col = global_start_col

        if token_type == INDENT:
            if start_line == 1:
                # Whole code-block is indented.
                global_start_col = end_col
            else:
                level += 1
            continue
        elif token_type == DEDENT:
            level -= 1
            continue
        elif token_type == COMMENT:
            continue

        if token_type == STRING and (prev_token_type in (NEWLINE, INDENT) or start_col == global_start_col):
            # Docstring
            out.append(" " * level + "0" + "\n" * string.count("\n"))
        elif start_line > prev_start_line and token_type != NEWLINE:
            # First op of a line, needs its minimized indent
            out.append(" " * level)  # Leading indent
            if string == "pass":
                out.append("0")  # Shorter than a ``pass`` statement.
            else:
                out.append(string)
        elif token_type == OP and prev_token_type not in _token_type_line_start:
            # No need for a space before operators.
            out.append(string)
        elif start_col > last_col and token_type != NEWLINE:
            if prev_token_type != OP:
                out.append(" ")
            out.append(string)
        else:
            out.append(string)

        prev_start_line = start_line
        last_col = end_col
        last_lineno = end_line

    return "".join(out)
