from pathlib import Path
from typing import Callable, Dict, Generator, List, Set, Union

PythonLiteral = Union[None, bool, bytes, int, float, str, List, Dict, Set]
BelayGenerator = Generator[PythonLiteral, None, None]
BelayReturn = Union[BelayGenerator, PythonLiteral]
BelayCallable = Callable[..., BelayReturn]

PathType = Union[str, Path]
