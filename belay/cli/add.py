from pathlib import Path
from typing import Optional

import tomlkit

from belay.cli.update import update
from belay.packagemanager.downloaders._package_json import _is_plain_package_name
from belay.packagemanager.downloaders.git import GitProviderUrl, InvalidGitUrlError, split_version_suffix
from belay.project import find_pyproject, project_cache


def _sanitize_package_name(name: str) -> str:
    """Convert string to valid Python identifier.

    Parameters
    ----------
    name : str
        Raw name extracted from URI.

    Returns
    -------
    str
        Sanitized package name.

    Raises
    ------
    ValueError
        If name cannot be converted to valid identifier.
    """
    # Remove .py extension
    if name.endswith(".py"):
        name = name[:-3]
    # Replace hyphens with underscores
    name = name.replace("-", "_")
    # Validate result
    if not name.isidentifier():
        raise ValueError(f"Cannot convert '{name}' to valid package name.")
    return name


def _parse_index_package(uri: str) -> Optional[str]:
    """Parse URI as an index package and return the dependency value.

    For index packages, returns the appropriate value:
    - "aiohttp" -> "*" (latest)
    - "aiohttp@1.0.0" -> "1.0.0" (specific version)
    - "mip:aiohttp" -> "*" (explicit mip prefix, latest)
    - "mip:aiohttp@1.0.0" -> "1.0.0" (explicit mip prefix, specific version)

    For non-index packages, returns None.

    Parameters
    ----------
    uri : str
        URI to check.

    Returns
    -------
    Optional[str]
        The dependency value if this is an index package, None otherwise.
    """
    base_uri, version = split_version_suffix(uri)

    # Handle mip: prefix (explicit index package)
    if base_uri.startswith("mip:"):
        return version if version else "*"

    # Handle plain package names (index lookup)
    if _is_plain_package_name(base_uri):
        return version if version else "*"

    return None


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
        return _sanitize_package_name(name)

    # Handle plain package names (index lookup)
    if _is_plain_package_name(base_uri):
        return _sanitize_package_name(base_uri)

    # Handle git provider URLs (shorthand and HTTPS, including repo root URLs)
    try:
        parsed = GitProviderUrl.parse(uri)
        return _sanitize_package_name(parsed.inferred_package_name)
    except InvalidGitUrlError:
        pass

    # Try local path (absolute or relative)
    if uri.startswith("/") or uri.startswith("./") or uri.startswith("../"):
        path = Path(uri)
        name = path.name
        return _sanitize_package_name(name)

    raise ValueError(f"Cannot infer package name from URI: {uri}")


def add(
    name_or_uri: str,
    uri: Optional[str] = None,
    *,
    group: str = "main",
    develop: bool = False,
    rename_to_init: bool = True,
    no_update: bool = False,
):
    """Add a dependency to pyproject.toml.

    Adds a new dependency to the specified group in pyproject.toml and
    optionally downloads it immediately.

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
    uri : str
        Source URI (GitHub URL, local path, etc.). If omitted, name_or_uri
        is treated as the URI and the package name is inferred.
    group : str
        Dependency group to add to. Defaults to "main".
    develop : bool
        Install in develop/editable mode (always re-download).
    rename_to_init : bool
        Rename single .py file to __init__.py.
    no_update : bool
        Skip downloading the dependency after adding.
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

    # Check if this is an index package (plain name or mip: prefix)
    index_value = _parse_index_package(uri)
    is_index_package = index_value is not None

    # For index packages, use the version/wildcard value; otherwise use the URI
    dep_value = index_value if is_index_package else uri

    # Index packages have their structure defined by package.json,
    # so rename_to_init is not applicable (use simple string format)
    use_rename_to_init = rename_to_init if not is_index_package else True

    pyproject_path = find_pyproject()
    _add_dependency_to_toml(
        pyproject_path=pyproject_path,
        package=package,
        uri=dep_value,
        group=group,
        develop=develop,
        rename_to_init=use_rename_to_init,
    )

    # Clear caches so update sees the new dependency
    project_cache.clear()

    if not no_update:
        update(package)


def _get_dependencies_table(doc, group: str):
    """Get or create the dependencies table for a group.

    Creates any missing intermediate tables ([tool], [tool.belay], etc.).

    Parameters
    ----------
    doc
        Parsed pyproject.toml document.
    group : str
        Dependency group ("main" or named group).

    Returns
    -------
    dict-like
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

    # Check if dependency already exists
    if package in deps:
        raise ValueError(
            f"Dependency '{package}' already exists in group '{group}'. "
            "Remove it first or manually edit pyproject.toml."
        )

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
