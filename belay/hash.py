from pathlib import Path
from typing import Union


def fnv1a(fn: Union[str, Path]) -> int:
    """Compute the FNV-1a 32-bit hash of a file."""
    fn = Path(fn)
    h = 0x811C9DC5
    size = 1 << 32
    with fn.open("rb") as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            for byte in data:
                h = h ^ byte
                h = (h * 0x01000193) % size
    return h
