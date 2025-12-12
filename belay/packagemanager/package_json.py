"""MicroPython package.json support for Belay.

This module provides support for MicroPython's package.json format,
including URL rewriting for github:/gitlab: shortcuts and index lookups.

See: https://docs.micropython.org/en/latest/reference/packages.html
"""

import hashlib
from typing import Optional
from urllib.parse import urlparse

import requests
from attrs import define, field

from belay.exceptions import PackageNotFoundError
from belay.packagemanager.downloaders._retry import fetch_url
from belay.packagemanager.downloaders.git import rewrite_url

__all__ = [
    "DEFAULT_MPY_VERSION",
    "DEFAULT_PACKAGE_INDICES",
    "HASH_LENGTH",
    "PackageJson",
    "compute_micropython_hash",
    "fetch_package_json",
    "is_index_hash",
]

DEFAULT_PACKAGE_INDICES = ("https://micropython.org/pi/v2",)
DEFAULT_MPY_VERSION = "py"

# MicroPython index hashes are 8 hex characters (truncated SHA256)
HASH_LENGTH = 8
_HEX_CHARS = frozenset("0123456789abcdefABCDEF")


def is_index_hash(source: str) -> bool:
    """Check if source string looks like a MicroPython index hash.

    MicroPython index hashes are exactly 8 hex characters (case-insensitive).

    Parameters
    ----------
    source
        Source string to check.

    Returns
    -------
    bool
        True if source appears to be an index hash.
    """
    return len(source) == HASH_LENGTH and all(c in _HEX_CHARS for c in source)


def compute_micropython_hash(content: bytes) -> str:
    """Compute MicroPython-style file hash (truncated SHA256).

    Parameters
    ----------
    content
        File content to hash.

    Returns
    -------
    str
        8-character lowercase hex hash.
    """
    return hashlib.sha256(content).hexdigest()[:HASH_LENGTH]


@define
class PackageJson:
    """Parsed MicroPython package.json manifest.

    Attributes
    ----------
    urls
        List of (destination_path, source_url) tuples for self-hosted packages.
    hashes
        List of (destination_path, hash) tuples for index-based packages.
    deps
        List of (package_name, version) dependency tuples.
    version
        Package version string.
    base_url
        Base URL for resolving relative URLs in this manifest.
    """

    urls: list[tuple[str, str]] = field(factory=list)
    hashes: list[tuple[str, str]] = field(factory=list)
    deps: list[tuple[str, str]] = field(factory=list)
    version: str = ""
    base_url: str = ""

    @classmethod
    def from_dict(cls, data: dict, base_url: str = "") -> "PackageJson":
        """Create PackageJson from parsed JSON dict.

        Parameters
        ----------
        data
            Parsed JSON dictionary.
        base_url
            Base URL for resolving relative URLs.

        Returns
        -------
        PackageJson
            Parsed package manifest.

        Raises
        ------
        ValueError
            If the package.json data is malformed.
        """
        try:
            urls = []
            for item in data.get("urls", []):
                if not isinstance(item, (list, tuple)) or len(item) != 2:
                    raise ValueError(f"Invalid urls entry: {item!r} (expected [dest, source])")
                urls.append((item[0], item[1]))

            hashes = []
            for item in data.get("hashes", []):
                if not isinstance(item, (list, tuple)) or len(item) != 2:
                    raise ValueError(f"Invalid hashes entry: {item!r} (expected [dest, hash])")
                hashes.append((item[0], item[1]))

            deps = []
            for item in data.get("deps", []):
                if not isinstance(item, (list, tuple)) or len(item) != 2:
                    raise ValueError(f"Invalid deps entry: {item!r} (expected [name, version])")
                deps.append((item[0], item[1]))

            version = data.get("version", "")
            if not isinstance(version, str):
                raise ValueError(f"Invalid version: {version!r} (expected string)")  # noqa: TRY004

            return cls(
                urls=urls,
                hashes=hashes,
                deps=deps,
                version=version,
                base_url=base_url,
            )
        except (TypeError, KeyError) as e:
            raise ValueError(f"Malformed package.json data: {e}") from e


def _is_url(s: str) -> bool:
    """Check if string looks like a URL vs package name."""
    return bool(urlparse(s).scheme)


def fetch_package_json(
    package: str,
    version: str = "latest",
    indices: Optional[list[str]] = None,
    mpy_version: str = DEFAULT_MPY_VERSION,
    timeout: float = 30.0,
) -> PackageJson:
    """Fetch package.json from index or URL.

    Parameters
    ----------
    package
        Package name or URL (github:, gitlab:, http://, https://).
    version
        Version string, default "latest".
    indices
        Package index URL(s). If None, uses DEFAULT_PACKAGE_INDICES.
        Indices are tried in order until the package is found.
    mpy_version
        MicroPython version for index lookup ("py", "6", etc.).
    timeout
        Request timeout in seconds.

    Returns
    -------
    PackageJson
        Parsed package manifest.

    Raises
    ------
    PackageNotFoundError
        If package cannot be found in any index.
    """
    if indices is None:
        indices = list(DEFAULT_PACKAGE_INDICES)

    # Determine if this is a URL or index package name
    if _is_url(package):
        url = rewrite_url(package)
        # Ensure URL points to package.json
        if not url.endswith(".json"):
            url = url.rstrip("/") + "/package.json"
        base_url = url.rsplit("/", 1)[0] + "/"

        try:
            response = fetch_url(url, timeout=timeout)
        except requests.exceptions.RequestException as e:
            raise PackageNotFoundError(f"Failed to fetch package: {package} (URL: {url}): {e}") from e

        if response.status_code == 404:
            raise PackageNotFoundError(f"Package not found: {package} (URL: {url})")

        data = response.json()
        return PackageJson.from_dict(data, base_url=base_url)

    # Index lookup - try each index in order
    for idx in indices:
        url = f"{idx}/package/{mpy_version}/{package}/{version}.json"
        try:
            response = fetch_url(url, timeout=timeout)
            if response.status_code == 404:
                continue

            data = response.json()
            return PackageJson.from_dict(data, base_url=f"{idx}/")
        except requests.exceptions.RequestException:
            continue

    raise PackageNotFoundError(f"Package not found in any index: {package}")
