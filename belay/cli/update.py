import ast
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlparse

import httpx
import tomli
from typer import Option


class NonMatchingURL(Exception):
    pass


def _strip_www(url: str):
    if url.startswith("www."):
        url = url[4:]
    return url


def _process_url_github(url: str):
    """Transforms github-like url into githubusercontent."""
    url = str(url)
    parsed = urlparse(url)
    netloc = _strip_www(parsed.netloc)
    if netloc == "github.com":
        # Transform to raw.githubusercontent
        _, user, project, mode, branch, *path = parsed.path.split("/")
        return f"https://raw.githubusercontent.com/{user}/{project}/{branch}/{'/'.join(path)}"
    elif netloc == "raw.githubusercontent.com":
        return f"https://raw.githubusercontent.com{parsed.path}"
    else:
        raise NonMatchingURL


def _process_url(url: str):
    parsers = [
        _process_url_github,
    ]
    for parser in parsers:
        try:
            return parser(url)
        except NonMatchingURL:
            pass

    # Unmodified URL
    return url


def _get_text(url: str):
    res = httpx.get(url)
    res.raise_for_status()
    return res.text


def _download_dependencies(
    dependencies: dict,
    local_dir: Union[str, Path] = ".belay-lib",
):
    local_dir = Path(local_dir)
    for pkg_name, dep in dependencies.items():
        if isinstance(dep, str):
            url = _process_url(dep)
            ext = Path(url).suffix
            if ext == ".py":
                # Single file
                target = local_dir / (pkg_name + ext)
                target.parent.mkdir(parents=True, exist_ok=True)

                code = _get_text(url)
                ast.parse(code)  # Check for valid python code

                with target.open("w") as f:
                    f.write(code)
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError


def _load_toml(path: Union[str, Path]):
    path = Path(path)

    with path.open("rb") as f:
        toml = tomli.load(f)

    try:
        toml = toml["tool"]["belay"]
    except KeyError:
        return {}

    return toml


def update(package: Optional[str] = Option(None)):
    toml = _load_toml("pyproject.toml")

    try:
        dependencies = toml["dependencies"]
    except KeyError:
        return

    _download_dependencies(dependencies)
