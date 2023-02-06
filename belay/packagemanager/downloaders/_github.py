import re
import shutil
from pathlib import Path

import git
import requests

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
        match = re.search(r"raw\.githubusercontent\.com/(.+?)/(.+?)/(.+?)/(.*)", uri)
    if not match:
        raise NonMatchingURI
    org, repo, ref, path = match.groups()

    githubusercontent_url = (
        f"https://raw.githubusercontent.com/{org}/{repo}/{ref}/{path}"
    )

    r = requests.get(githubusercontent_url)

    if r.status_code == 200:
        # Provided URI is a single file.
        dst /= Path(path).name
        dst.write_bytes(r.content)
    elif r.status_code == 404:
        # Probably a folder; use git.
        from belay.project import find_cache_folder

        repo_url = f"https://github.com/{org}/{repo}.git"
        repo_folder = find_cache_folder() / f"git-github-{org}-{repo}"
        repo_folder.mkdir(exist_ok=True, parents=True)

        # Check if we have already cloned
        if (repo_folder / ".git").is_dir():
            # Already been cloned
            repo = git.Repo(repo_folder)
            origin = repo.remote("origin")
            origin.fetch()
        else:
            repo = git.Repo.clone_from(repo_url, repo_folder)

        # Set to specified reference
        commit = repo.rev_parse(ref)
        repo.head.reference = commit
        repo.head.reset(index=True, working_tree=True)

        shutil.copytree(repo_folder / path, dst, dirs_exist_ok=True)
    else:
        r.raise_for_status()

    return dst
