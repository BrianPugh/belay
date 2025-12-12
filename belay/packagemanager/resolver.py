"""Recursive dependency resolver for MicroPython packages.

This module resolves MicroPython package.json dependencies recursively,
handling cycle detection and version conflicts.

Example
-------
>>> resolved = resolve_dependencies("aiohttp")
>>> for pkg in resolved:
...     for f in pkg.files:
...         download(f.source_url, f.dest_path)
"""

__all__ = [
    "CircularDependencyError",
    "ResolvedFile",
    "ResolvedPackage",
    "resolve_dependencies",
    "resolve_file_url",
]

import logging
from typing import Optional
from urllib.parse import urljoin

from attrs import define, field

from belay.packagemanager.downloaders.git import GitProviderUrl, InvalidGitUrlError
from belay.packagemanager.package_json import (
    DEFAULT_MPY_VERSION,
    DEFAULT_PACKAGE_INDICES,
    PackageJson,
    fetch_package_json,
    is_index_hash,
)

logger = logging.getLogger(__name__)


def _normalize_package_name(package: str) -> str:
    """Normalize package name for comparison.

    Handles github:/gitlab: URLs by extracting a canonical identifier.
    All names are lowercased for consistent comparison.
    """
    try:
        parsed = GitProviderUrl.parse(package)
    except InvalidGitUrlError:
        return package.lower()
    return parsed.canonical_id


def resolve_file_url(
    pkg_json: PackageJson,
    dest_path: str,
    source: str,
) -> str:
    """Resolve a file URL from package.json entry.

    Handles:
    - Absolute URLs (http://, https://)
    - Shorthand URLs (github:, gitlab:)
    - Relative URLs (resolved against base_url)
    - Hash-based index files (uses base_url to determine index)

    Parameters
    ----------
    pkg_json
        The PackageJson containing this file reference.
    dest_path
        Destination path for the file.
    source
        Source URL or hash from package.json.

    Returns
    -------
    str
        Full URL to download the file from.
    """
    # Check if source is a hash (for index packages)
    # Uses centralized hash detection logic
    if is_index_hash(source):
        # Hash-based lookup - derive index from base_url
        # base_url is set to "{index}/" when fetched from an index
        index = pkg_json.base_url.rstrip("/")
        return f"{index}/file/{source[:2]}/{source}"

    # Rewrite shorthand URLs (github:, gitlab:)
    try:
        parsed = GitProviderUrl.parse(source)
    except InvalidGitUrlError:
        pass
    else:
        return parsed.raw_url

    # Absolute URL
    if source.startswith(("http://", "https://")):
        return source

    # Relative URL - resolve against base
    return urljoin(pkg_json.base_url, source)


class CircularDependencyError(Exception):
    """Circular dependency detected during resolution."""


@define
class ResolvedFile:
    """A single file to be downloaded and installed.

    Represents one entry from a package.json's ``urls`` or ``hashes`` field.
    In package.json, files are specified as::

        "urls": [[dest_path, source_url], ...]
        "hashes": [[dest_path, hash], ...]

    For ``urls``, the source is a URL (absolute, relative, or shorthand like ``github:``).
    For ``hashes``, the source is an 8-char hex hash used to construct the index URL.

    Attributes
    ----------
    dest_path
        Where to install the file on the device, relative to the installation
        directory. E.g., ``"mlx90640/__init__.py"``.
    source_url
        Full URL to download the file from. This is the resolved form of the
        source from package.json (relative URLs made absolute, shorthand expanded).
    hash
        Optional 8-char hex hash for integrity verification. Present for files
        from the MicroPython index (``hashes`` field), ``None`` for URL-based
        packages (``urls`` field).
    """

    dest_path: str
    source_url: str
    hash: Optional[str] = None


@define
class ResolvedPackage:
    """A fully resolved package with all its files ready for download.

    Created by :func:`resolve_dependencies` after parsing a package.json manifest.
    Contains the list of :class:`ResolvedFile` entries that need to be downloaded
    and installed for this package.

    Note that dependencies are resolved separately - each dependency becomes
    its own :class:`ResolvedPackage` in the output dict.

    Attributes
    ----------
    name
        Package name or URL identifier (e.g., ``"aiohttp"`` or ``"github:user/repo"``).
    version
        Resolved version string from package.json, or the requested version
        if the manifest didn't specify one.
    files
        List of :class:`ResolvedFile` to download for this package. Each file
        specifies both where to download from (:attr:`~ResolvedFile.source_url`)
        and where to install (:attr:`~ResolvedFile.dest_path`).
    """

    name: str
    version: str
    files: list[ResolvedFile] = field(factory=list)


def resolve_dependencies(
    package: str,
    version: str = "latest",
    indices: Optional[list[str]] = None,
    mpy_version: str = DEFAULT_MPY_VERSION,
) -> list[ResolvedPackage]:
    """Resolve a package and all its dependencies.

    Given a package name or URL, fetches its package.json manifest, extracts
    file URLs, and recursively resolves all dependencies. The output is a
    list of :class:`ResolvedPackage` objects, each containing the files
    to download.

    Resolution process:

    1. Fetch package.json for the requested package
    2. Extract file entries from ``urls`` and ``hashes`` fields
    3. Recursively resolve packages listed in ``deps`` field
    4. Return all resolved packages as a list

    Handles:

    - Index packages: looked up by name (e.g., ``"aiohttp"``)
    - URL packages: fetched directly (e.g., ``"github:user/repo"``)
    - Circular dependency detection (raises :class:`CircularDependencyError`)
    - Version conflicts (first-wins strategy with warning)

    Parameters
    ----------
    package
        Package name or URL.
    version
        Version constraint. Default: ``"latest"``.
    indices
        Package index URL(s) for name-based lookups. If None, uses DEFAULT_PACKAGE_INDICES.
        Indices are tried in order until the package is found.
    mpy_version
        MicroPython version for index lookups (``"py"`` for pure Python,
        ``"6"`` for .mpy format version 6, etc.). Default: ``"py"``.

    Returns
    -------
    list[ResolvedPackage]
        List of resolved packages.

    Raises
    ------
    CircularDependencyError
        If circular dependency detected.
    PackageNotFoundError
        If package cannot be found.

    Examples
    --------
    >>> resolved = resolve_dependencies("aiohttp")
    >>> for pkg in resolved:
    ...     print(f"{pkg.name} v{pkg.version}: {len(pkg.files)} files")
    ...     for f in pkg.files:
    ...         print(f"  {f.dest_path} <- {f.source_url}")
    """
    if indices is None:
        indices = list(DEFAULT_PACKAGE_INDICES)

    # Resolution state (captured by closure)
    resolved: list[ResolvedPackage] = []
    in_progress: set[str] = set()
    version_map: dict[str, str] = {}

    def _resolve_recursive(pkg: str, ver: str) -> None:
        """Internal recursive resolution."""
        # Normalize package name for dedup and cycle detection
        # Use package name (not version) for cycle detection to catch A@1.0 -> B -> A@2.0
        pkg_name_normalized = _normalize_package_name(pkg)

        # Check for version conflicts (same package, different version)
        if pkg_name_normalized in version_map:
            existing_version = version_map[pkg_name_normalized]
            if existing_version != ver:
                logger.warning(
                    f"Version conflict for {pkg}: already resolved {existing_version}, "
                    f"now requested {ver}. Using first-resolved version."
                )
            # Already resolved (possibly with different version) - skip
            return

        # Cycle detection using package name (regardless of version)
        if pkg_name_normalized in in_progress:
            raise CircularDependencyError(f"Circular dependency detected: {pkg} (in resolution chain)")

        in_progress.add(pkg_name_normalized)

        try:
            # Fetch and parse package.json
            pkg_json = fetch_package_json(
                pkg,
                version=ver,
                indices=indices,
                mpy_version=mpy_version,
            )

            # Resolve files
            files = []

            # Handle urls field (self-hosted packages) - no hash verification
            for dest, source in pkg_json.urls:
                url = resolve_file_url(pkg_json, dest, source)
                files.append(
                    ResolvedFile(
                        dest_path=dest,
                        source_url=url,
                    )
                )

            # Handle hashes field (index packages) - with hash verification
            for dest, hash_val in pkg_json.hashes:
                url = resolve_file_url(pkg_json, dest, hash_val)
                files.append(
                    ResolvedFile(
                        dest_path=dest,
                        source_url=url,
                        hash=hash_val,
                    )
                )

            # Recursively resolve dependencies BEFORE marking as resolved
            # This ensures cycle detection works properly
            for dep_name, dep_version in pkg_json.deps:
                _resolve_recursive(dep_name, dep_version)

            # Record the resolved version
            resolved_version = pkg_json.version or ver
            version_map[pkg_name_normalized] = resolved_version

            # Store resolved package AFTER all dependencies are resolved
            resolved.append(
                ResolvedPackage(
                    name=pkg,
                    version=resolved_version,
                    files=files,
                )
            )
        finally:
            # Clean up in_progress even if resolution fails
            in_progress.discard(pkg_name_normalized)

    _resolve_recursive(package, version)
    return resolved
