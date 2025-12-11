"""Common download utilities."""

import shutil
from pathlib import Path
from urllib.parse import urlparse

import fsspec

from belay.packagemanager.downloaders.git import GitProviderUrl, InvalidGitUrlError
from belay.typing import PathType


class NonMatchingURI(Exception):  # noqa: N818
    """Provided URI does not match downloading function."""


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

    if Path(uri).is_dir():  # local
        shutil.copytree(uri, dst, dirs_exist_ok=True)
    else:
        with fsspec.open(uri, "rb") as f:
            data = f.read()

        dst /= Path(uri).name
        with dst.open("wb") as f:
            f.write(data)

    return dst


def download_uri(dst_folder: PathType, uri: str) -> Path:
    """Download ``uri`` to destination folder.

    Tries providers in order:
    1. Git providers (GitHub, GitLab) via GitProviderUrl
    2. Package.json packages (mip:, github:user/repo without path)
    3. Generic download (local files, http URLs)

    Parameters
    ----------
    dst_folder
        Destination folder.
    uri
        URI to download.

    Returns
    -------
    Path
        Path to downloaded content.
    """
    dst_folder = Path(dst_folder)

    # Try git providers for single file downloads
    try:
        parsed = GitProviderUrl.parse(uri)
        if parsed.has_file_extension():
            # Has a file extension - download as single file
            return parsed.download(dst_folder)
    except InvalidGitUrlError:
        pass

    # Try package.json handler (for mip: and package references)
    from belay.packagemanager.downloaders._package_json import download_package_json

    # Load project config for package index settings (if pyproject.toml exists)
    try:
        from belay.project import load_pyproject

        config = load_pyproject()
        indices = config.package_indices
        mpy_version = config.mpy_version
    except FileNotFoundError:
        # No pyproject.toml found - use defaults (this is expected for standalone use)
        indices = None
        mpy_version = None
    except Exception:
        # Config parsing errors (TOML syntax, validation, etc.) - use defaults
        # rather than failing the download. The user will see errors when they
        # explicitly run config-dependent commands.
        indices = None
        mpy_version = None

    try:
        return download_package_json(dst_folder, uri, indices=indices, mpy_version=mpy_version)
    except NonMatchingURI:
        pass

    # Fall back to generic download
    return _download_generic(dst_folder, uri)
