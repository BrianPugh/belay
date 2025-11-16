from collections.abc import Generator
from pathlib import Path
from typing import Callable, Union

PythonLiteral = Union[None, bool, bytes, int, float, str, list, dict, set]
BelayGenerator = Generator[PythonLiteral, None, None]
BelayReturn = Union[BelayGenerator, PythonLiteral]
BelayCallable = Callable[..., BelayReturn]

PathType = Union[str, Path]
