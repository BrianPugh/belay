from pathlib import Path

import fsspec
from autoregistry import Registry

from belay.typing import PathType


class NonMatchingURI(Exception):
    pass


downloaders = Registry()


# DO NOT decorate with ``@downloaders``, since this must be last.
def _download_generic(dst: Path, uri: str):
    """Downloads a single file to ``dst / "__init__.py"``."""
    try:
        with fsspec.open(uri, "rb") as f:
            data = f.read()

        dst /= "__init__.py"
        with dst.open("wb") as f:
            f.write(data)
    except IsADirectoryError:
        fs = fsspec.filesystem("file")
        fs.get(uri, dst.as_posix(), recursive=True)


def download_uri(dst_folder: PathType, uri: str):
    """Download ``uri`` by trying all downloaders on ``uri`` until one works."""
    dst_folder = Path(dst_folder)
    for processor in downloaders.values():
        try:
            processor(dst_folder, uri)
            break
        except NonMatchingURI:
            pass
    else:
        _download_generic(dst_folder, uri)
