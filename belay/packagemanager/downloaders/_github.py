import re
from pathlib import Path

import fsspec

from .common import NonMatchingURI, downloaders


@downloaders
def github(dst: Path, uri: str):
    """Download a file or folder from github."""
    # Single File Website; e.g.:
    #     https://github.com/BrianPugh/belay/blob/main/belay/__init__.py
    match = re.search(r"github\.com/(.+?)/(.+?)/blob/(.+?)/(.*)", uri)
    if not match:
        # Folder; e.g.:
        #     https://github.com/BrianPugh/belay/tree/main/belay
        match = re.search(r"github\.com/(.+?)/(.+?)/tree/(.+?)/(.*)", uri)
    if not match:
        raise NonMatchingURI
    org, repo, sha, path = match.groups()

    fs = fsspec.filesystem("github", org=org, repo=repo, sha=sha)

    if not fs.isdir(path):
        dst = dst / "__init__.py"
    fs.get(path, str(dst), recursive=True)
