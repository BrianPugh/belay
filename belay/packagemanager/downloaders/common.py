from pathlib import Path
from urllib.parse import urlparse

import fsspec
from autoregistry import Registry

from belay.typing import PathType

# Downloaders should have function signature
#    def downloader(dst: Path, uri: str) -> Path
# where the return value is one of:
#    1. ``dst`` if a folder was downloaded
#    2. Path to single file if the URI was for a single file.
downloaders = Registry()


class NonMatchingURI(Exception):
    """Provided URI does not match downloading function."""


# DO NOT decorate with ``@downloaders``, since this must be last.
def _download_generic(dst: Path, uri: str) -> Path:
    """Downloads a single file or folder to ``dst / <filename>``."""
    parsed = urlparse(uri)

    if parsed.scheme in ("", "file"):
        # Local file, make it relative to project root
        uri_path = Path(uri)

        if not uri_path.is_absolute():
            from belay.project import find_project_folder

            uri_path = find_project_folder() / uri

        uri = str(uri_path)

    if Path(uri).is_dir():
        fs = fsspec.filesystem("file")
        fs.get(uri, str(dst), recursive=True)
    else:
        with fsspec.open(uri, "rb") as f:
            data = f.read()

        dst /= Path(uri).name
        with dst.open("wb") as f:
            f.write(data)

    return dst


def download_uri(dst_folder: PathType, uri: str) -> Path:
    """Download ``uri`` by trying all downloaders on ``uri`` until one works."""
    dst_folder = Path(dst_folder)
    for processor in downloaders.values():
        try:
            return processor(dst_folder, uri)
            break
        except NonMatchingURI:
            pass
    else:
        return _download_generic(dst_folder, uri)
