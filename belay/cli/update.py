from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
import pytest
import tomli
from typer import Option


class NonMatchingURL(Exception):
    pass


def _strip_www(url: str):
    if url.startswith("www."):
        url = url[4:]
    return url


def _process_url_github(url: str):
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


def _process_url(url):
    for parser in [_process_url_github]:
        try:
            return parser(url)
        except NonMatchingURL:
            pass

    # Unmodified URL
    return url


def update(package: Optional[str] = Option(None)):
    pyproject = Path("pyproject.toml")

    with pyproject.open("rb") as f:
        toml = tomli.load(f)

    try:
        toml = toml["tool"]["belay"]
    except KeyError:
        return

    try:
        dependencies = toml["dependencies"]
    except KeyError:
        return

    for pkg_name, url in dependencies.items():
        res = httpx.get(url)
        raise NotImplementedError

    raise NotImplementedError
