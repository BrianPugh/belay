"""Downloader for MicroPython package.json packages.

This module handles downloading packages that use the MicroPython package.json
format, including packages from the micropython.org index and GitHub/GitLab
repositories.
"""

from pathlib import Path
from typing import Optional

import requests

from belay.exceptions import IntegrityError, PackageNotFoundError
from belay.packagemanager.downloaders._retry import fetch_url
from belay.packagemanager.downloaders.common import NonMatchingURI
from belay.packagemanager.downloaders.git import GitProviderUrl, InvalidGitUrlError, split_version_suffix
from belay.packagemanager.package_json import (
    DEFAULT_MPY_VERSION,
    DEFAULT_PACKAGE_INDICES,
    compute_micropython_hash,
)
from belay.packagemanager.resolver import resolve_dependencies


def _is_plain_package_name(name: str) -> bool:
    """Check if string looks like a plain package name (not a URL or path).

    Plain package names:
    - Contain only alphanumeric characters, underscores, and hyphens
    - Don't contain path separators or URL schemes
    - Don't have file extensions

    Parameters
    ----------
    name
        String to check.

    Returns
    -------
    bool
        True if string looks like a plain package name.
    """
    if not name:
        return False

    # Check for URL schemes or path indicators
    if ":" in name or "/" in name or "\\" in name:
        return False

    # Check for file extensions (common ones that would indicate a file, not a package)
    if "." in name:
        return False

    # Check characters are valid for package names
    # MicroPython packages use alphanumeric, underscores, and hyphens
    return all(c.isalnum() or c in "_-" for c in name)


def _is_package_json_uri(uri: str) -> bool:
    """Determine if URI should be handled as package.json.

    Detection logic:
    - Plain package names (e.g., "aiohttp") -> index lookup
    - Explicit mip: prefix (e.g., "mip:aiohttp") -> index lookup
    - Explicit .json URLs -> package.json
    - github:org/repo (no file path) -> package.json at root
    - github:org/repo/package.json or .json suffix -> explicit package.json
    - github:org/repo/file.py -> NOT package.json (single file)
    - gitlab: same patterns as github:

    Parameters
    ----------
    uri
        URI to check.

    Returns
    -------
    bool
        True if this URI should be handled as a package.json reference.
    """
    # Extract version suffix if present (e.g., "github:user/repo@v1.0", "aiohttp@1.0")
    base_uri, _ = split_version_suffix(uri)

    # Plain package name (e.g., "aiohttp", "ntptime", "micropython-lib")
    if _is_plain_package_name(base_uri):
        return True

    # Explicit .json URL
    if base_uri.endswith(".json"):
        return True

    # Explicit MicroPython index prefix (mip:package_name)
    if base_uri.startswith("mip:"):
        return True

    # github:/gitlab: shorthand (MicroPython package.json convention)
    try:
        parsed = GitProviderUrl.parse(uri)
        # No path -> package.json at root
        # Path with no file extension -> directory, assume package.json
        # Path ending in .json -> explicit package.json
        # Path with non-.json extension -> single file, NOT package.json
        if not parsed.path:
            return True
        return not parsed.has_file_extension() or parsed.path.endswith(".json")
    except InvalidGitUrlError:
        return False


def download_package_json(
    dst: Path,
    uri: str,
    indices: Optional[list[str]] = None,
    mpy_version: str = DEFAULT_MPY_VERSION,
) -> Path:
    """Download a MicroPython package.json-based package.

    This downloader handles:
    - MicroPython index packages (e.g., "mip:aiohttp", "mip:ntptime@1.0.0")
    - GitHub repositories (e.g., "github:user/repo", "github:user/repo@tag")
    - GitLab repositories (e.g., "gitlab:user/repo")
    - Explicit package.json URLs

    Parameters
    ----------
    dst
        Destination directory for downloaded files.
    uri
        Package name or URL.
    indices
        Package index URL(s) for name-based lookups. If None, uses DEFAULT_PACKAGE_INDICES.
    mpy_version
        MicroPython version for index lookups ("py" for pure Python,
        "6" for .mpy format version 6, etc.).

    Returns
    -------
    Path
        Destination directory.

    Raises
    ------
    NonMatchingURI
        If URI is not a package.json reference.
    PackageNotFoundError
        If package cannot be found or downloaded.
    """
    if not _is_package_json_uri(uri):
        raise NonMatchingURI(f"Not a package.json URI: {uri}")

    if indices is None:
        indices = list(DEFAULT_PACKAGE_INDICES)

    # Parse version from URI if present
    package, version = split_version_suffix(uri)
    if version is None:
        version = "latest"

    # Strip mip: prefix if present (explicit index package)
    if package.startswith("mip:"):
        package = package[4:]

    # Resolve package and dependencies
    resolved = resolve_dependencies(package, version, indices=indices, mpy_version=mpy_version)

    # Download all files
    for pkg in resolved:
        for file_info in pkg.files:
            _download_file(dst, file_info.dest_path, file_info.source_url, file_info.hash)

    return dst


def _download_file(
    dst: Path,
    dest_path: str,
    source_url: str,
    expected_hash: Optional[str] = None,
    timeout: float = 30.0,
) -> None:
    """Download a single file with retry logic and optional hash verification.

    Parameters
    ----------
    dst
        Base destination directory.
    dest_path
        Relative path within destination.
    source_url
        URL to download from.
    expected_hash
        Optional hash to verify (8-char hex from MicroPython index).
    timeout
        Request timeout in seconds.

    Raises
    ------
    PackageNotFoundError
        If download fails.
    IntegrityError
        If hash verification fails.
    """
    file_path = dst / dest_path
    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        response = fetch_url(source_url, timeout=timeout)
        response.raise_for_status()
        content = response.content
    except requests.exceptions.RequestException as e:
        raise PackageNotFoundError(f"Failed to download {source_url}: {e}") from e

    # Verify hash if provided (case-insensitive comparison)
    if expected_hash:
        actual_hash = compute_micropython_hash(content)
        if actual_hash.lower() != expected_hash.lower():
            raise IntegrityError(f"Hash mismatch for {dest_path}: expected {expected_hash}, got {actual_hash}")

    file_path.write_bytes(content)
