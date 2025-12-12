from pathlib import Path
from typing import Optional

import tomlkit
import tomlkit.items

from belay.helpers import sanitize_package_name
from belay.packagemanager.downloaders._package_json import _is_package_json_uri, _is_plain_package_name
from belay.packagemanager.downloaders.git import GitProviderUrl, InvalidGitUrlError, split_version_suffix
from belay.packagemanager.group import Group
from belay.project import find_pyproject


def _is_local_path(uri: str) -> bool:
    """Check if URI is a local filesystem path."""
    return Path(uri).is_absolute() or uri.startswith("/") or uri.startswith("./") or uri.startswith("../")


def infer_package_name(uri: str) -> str:
    """Infer package name from URI.

    Uses smart inference based on URI type:
    - Plain package names: use directly (e.g., "aiohttp")
    - mip: prefix: strip prefix (e.g., "mip:aiohttp" -> "aiohttp")
    - github:/gitlab: shorthand: use repo name or last path component
    - GitHub/GitLab URLs: prefer last path component, fall back to repo name
    - Local paths: use final component

    Parameters
    ----------
    uri : str
        Source URI (package name, GitHub URL, local path, etc.).

    Returns
    -------
    str
        Inferred package name (valid Python identifier).

    Raises
    ------
    ValueError
        If package name cannot be inferred.
    """
    # Strip version suffix for name inference
    base_uri, _ = split_version_suffix(uri)

    # Handle mip: prefix (explicit index package)
    if base_uri.startswith("mip:"):
        name = base_uri[4:]  # Strip "mip:" prefix
        return sanitize_package_name(name)

    # Handle plain package names (index lookup)
    if _is_plain_package_name(base_uri):
        return sanitize_package_name(base_uri)

    # Handle git provider URLs (shorthand and HTTPS, including repo root URLs)
    try:
        parsed = GitProviderUrl.parse(uri)
        return sanitize_package_name(parsed.inferred_package_name)
    except InvalidGitUrlError:
        pass

    # Try local path (absolute or relative, cross-platform)
    if _is_local_path(uri):
        return sanitize_package_name(Path(uri).name)

    raise ValueError(f"Cannot infer package name from URI: {uri}")


def add(
    name_or_uri: str,
    uri: Optional[str] = None,
    *,
    group: str = "main",
    develop: bool = False,
    rename_to_init: bool = True,
):
    """Add a dependency to pyproject.toml.

    Downloads the dependency first, then adds it to pyproject.toml only
    if the download succeeds.

    If only a URI is provided, the package name is inferred from it.

    Supports various URI formats:
    - Index packages: "aiohttp", "aiohttp@1.0.0", "mip:aiohttp"
    - GitHub/GitLab shorthand: "github:user/repo", "gitlab:user/repo@tag"
    - Full URLs: "https://github.com/user/repo/blob/main/file.py"
    - Local paths: "./local/path", "/absolute/path"

    Parameters
    ----------
    name_or_uri : str
        Package name (if uri is provided) or source URI (if uri is omitted).
    uri : Optional[str]
        Source URI (GitHub URL, local path, etc.). If omitted, name_or_uri
        is treated as the URI and the package name is inferred.
    group : str
        Dependency group to add to. Defaults to "main".
    develop : bool
        Install in develop/editable mode (always re-download). Only valid for local paths.
    rename_to_init : bool
        Rename single .py file to __init__.py.
    """
    if uri is None:
        # Single argument: name_or_uri is actually the URI
        uri = name_or_uri
        package = infer_package_name(uri)
    else:
        # Two arguments: name_or_uri is the package name
        package = name_or_uri

    if not package.isidentifier():
        raise ValueError(f"Package name '{package}' must be a valid Python identifier.")

    if develop and not _is_local_path(uri):
        raise ValueError("--develop can only be used with local paths (e.g., ./path, ../path, /absolute/path)")

    # Index packages have their structure defined by package.json,
    # so rename_to_init is ignored. We set use_rename_to_init to True
    # as a safe default that won't interfere with package.json behavior.
    is_index_package = _is_package_json_uri(uri)
    use_rename_to_init = rename_to_init if not is_index_package else True

    # Check for existing dependency before downloading
    pyproject_path = find_pyproject()
    _check_dependency_not_exists(pyproject_path, package, group)

    # Build dependency config and download first
    dep_config = {package: _build_dependency_value(uri, develop, use_rename_to_init)}
    temp_group = Group(name=group, dependencies=dep_config)
    temp_group._download_package(package)

    # Download succeeded - now add to pyproject.toml
    _add_dependency_to_toml(
        pyproject_path=pyproject_path,
        package=package,
        uri=uri,
        group=group,
        develop=develop,
        rename_to_init=use_rename_to_init,
    )


def _build_dependency_value(uri: str, develop: bool, rename_to_init: bool):
    """Build the dependency value for Group config.

    Parameters
    ----------
    uri : str
        Source URI for the dependency.
    develop : bool
        Whether this is a develop/editable dependency.
    rename_to_init : bool
        Whether to rename single .py to __init__.py.

    Returns
    -------
    str or dict
        Dependency value suitable for GroupConfig.
    """
    if develop or not rename_to_init:
        value = {"uri": uri}
        if develop:
            value["develop"] = True
        if not rename_to_init:
            value["rename_to_init"] = False
        return value
    return uri


def _check_dependency_not_exists(pyproject_path: Path, package: str, group: str):
    """Check that a dependency doesn't already exist.

    Parameters
    ----------
    pyproject_path : Path
        Path to pyproject.toml.
    package : str
        Package name to check.
    group : str
        Dependency group ("main" or named group).

    Raises
    ------
    ValueError
        If the dependency already exists.
    """
    content = pyproject_path.read_text(encoding="utf-8")
    doc = tomlkit.parse(content)

    try:
        if group == "main":
            deps = doc["tool"]["belay"]["dependencies"]
        else:
            deps = doc["tool"]["belay"]["group"][group]["dependencies"]

        if package in deps:
            raise ValueError(
                f"Dependency '{package}' already exists in group '{group}'. "
                "Remove it first or manually edit pyproject.toml."
            )
    except KeyError:
        # Section doesn't exist yet, so dependency definitely doesn't exist
        pass


def _get_dependencies_table(doc: tomlkit.TOMLDocument, group: str) -> tomlkit.items.Table:
    """Get or create the dependencies table for a group.

    Creates any missing intermediate tables ([tool], [tool.belay], etc.).

    Parameters
    ----------
    doc : tomlkit.TOMLDocument
        Parsed pyproject.toml document.
    group : str
        Dependency group ("main" or named group).

    Returns
    -------
    tomlkit.items.Table
        The dependencies table for the specified group.
    """
    if "tool" not in doc:
        doc["tool"] = tomlkit.table()
    if "belay" not in doc["tool"]:
        doc["tool"]["belay"] = tomlkit.table()

    belay = doc["tool"]["belay"]

    if group == "main":
        if "dependencies" not in belay:
            belay["dependencies"] = tomlkit.table()
        return belay["dependencies"]
    else:
        if "group" not in belay:
            belay["group"] = tomlkit.table()
        if group not in belay["group"]:
            belay["group"][group] = tomlkit.table()
        if "dependencies" not in belay["group"][group]:
            belay["group"][group]["dependencies"] = tomlkit.table()
        return belay["group"][group]["dependencies"]


def _add_dependency_to_toml(
    pyproject_path: Path,
    package: str,
    uri: str,
    group: str,
    develop: bool,
    rename_to_init: bool,
):
    """Add a dependency entry to pyproject.toml.

    Parameters
    ----------
    pyproject_path : Path
        Path to pyproject.toml.
    package : str
        Package name (must be valid Python identifier).
    uri : str
        Source URI for the dependency.
    group : str
        Dependency group ("main" or named group).
    develop : bool
        Whether to mark as develop/editable dependency.
    rename_to_init : bool
        Whether to rename single .py to __init__.py.
    """
    content = pyproject_path.read_text(encoding="utf-8")
    doc = tomlkit.parse(content)
    deps = _get_dependencies_table(doc, group)

    # Create dependency value based on options
    if develop or not rename_to_init:
        # Need full dict specification
        dep_value = tomlkit.inline_table()
        dep_value["uri"] = uri
        if develop:
            dep_value["develop"] = True
        if not rename_to_init:
            dep_value["rename_to_init"] = False
    else:
        # Simple string format (most common case)
        dep_value = uri

    deps[package] = dep_value

    pyproject_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
