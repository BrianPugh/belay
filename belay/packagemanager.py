import ast
import hashlib
import re
import shutil
import tempfile
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

import fsspec
from autoregistry import Registry
from rich.console import Console

PathType = Union[str, Path]


class NonMatchingURI(Exception):
    pass


downloaders = Registry()


# TODO: maybe use pydantic.dataclass
@dataclass
class GroupConfig:
    """Schema and store of a group defined in ``pyproject.toml``.

    Don't put any methods in here, they go in ``Group``.
    Don't directly instnatiate ``GroupConfig`` outside of ``Config``.
    This class is primarily for namespacing and validation.
    """

    name: str
    optional: bool = False
    dependencies: Dict[str, Union[list, dict, str]] = field(default_factory=dict)


class Group:
    """Represents a group defined in ``pyproject.toml``."""

    def __init__(self, *args, **kwargs):
        from belay.project import find_dependencies_folder

        self.config = GroupConfig(*args, **kwargs)

        self.folder = find_dependencies_folder() / self.config.name

        if self.config.optional:
            raise NotImplementedError("Optional groups not implemented yet.")

    def __eq__(self, other):
        if not isinstance(other, Group):
            return False
        return self.config.__dict__ == other.config.__dict__

    def __repr__(self):
        kws = [f"{key}={value!r}" for key, value in self.config.__dict__.items()]
        return f"{type(self).__name__}({', '.join(kws)})"

    @property
    def dependencies(self):
        return self.config.dependencies

    def clean(self):
        """Delete any dependency module not specified in ``self.config.dependencies``."""
        dependencies = set(self.dependencies)
        existing_deps = []

        if not self.folder.exists():
            return

        existing_deps.extend(self.folder.glob("*"))

        for existing_dep in existing_deps:
            if existing_dep.stem in dependencies:
                continue
            existing_dep.unlink()

    def copy_to(self, dst):
        """Copy Dependencies folder to destination directory."""
        if self.folder.exists():
            shutil.copytree(self.folder, dst, dirs_exist_ok=True)

    def download(
        self,
        packages: Optional[List[str]] = None,
        console: Optional[Console] = None,
    ):
        """Download dependencies.

        Parameters
        ----------
        packages: Optional[List[str]]
            Only download these package.
        console: Optional[Console]
            Print progress out to console.
        """
        if packages is None:
            # Update all packages
            packages = list(self.dependencies.keys())

        if not packages:
            return

        if console:
            cm = console.status("[bold green]Updating Dependencies")
        else:
            cm = nullcontext()

        def log(*args, **kwargs):
            if console:
                console.log(*args, **kwargs)

        with cm:
            for package_name in packages:
                local_folder = self.folder / package_name
                local_folder.mkdir(exist_ok=True, parents=True)

                dep_src = self.dependencies[package_name]

                if isinstance(dep_src, str):
                    # TODO: as we allow dict dependency specifiers, this should mirror it.
                    dep_src = {"remote": dep_src}
                elif isinstance(dep_src, list):
                    raise NotImplementedError("List dependencies not yet supported.")
                elif not isinstance(dep_src, dict):
                    raise NotImplementedError(
                        "Dictionary dependencies not yet supported."
                    )

                log(f"{package_name}: Updating...")

                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_dir = Path(tmp_dir)
                    _download_uri(tmp_dir, dep_src["remote"])
                    _verify_files(tmp_dir)
                    changed = _sync(tmp_dir, local_folder)

                if changed:
                    log(f"[bold green]{package_name}: Updated.")
                else:
                    log(f"{package_name}: No changes detected.")

                # Detect if an old single-py file exists and remove it from
                # older version of Belay. We can eventually remove this check
                # after enough time has passed.
                local_folder.with_suffix(".py").unlink(missing_ok=True)


@downloaders
def _download_github(dst: Path, uri: str):
    """Download a file or folder from github."""
    # Single File
    match = re.search(r"github\.com/(.+?)/(.+?)/blob/(.+?)/(.*)", uri)
    if not match:
        # Folder
        match = re.search(r"github\.com/(.+?)/(.+?)/tree/(.+?)/(.*)", uri)
    if not match:
        raise NonMatchingURI
    org, repo, branch, path = match.groups()

    # TODO: use github username/token from env-var, but first need to
    #       figure out pyproject interface. Or maybe something with SSH?
    username, token = None, None
    # username = os.environ.get("GITHUB_USERNAME")
    # token = os.environ.get("GITHUB_TOKEN")

    fs = fsspec.filesystem("github", org=org, repo=repo, username=username, token=token)
    if not fs.isdir(path):
        dst = dst / "__init__.py"
    fs.get(path, dst.as_posix(), recursive=True)


# DO NOT decorate with ``@downloaders``, since this must be last.
def _download_generic(dst: Path, uri: str):
    """Downloads a single file to ``dst / "__init__.py"``."""
    dst = dst / "__init__.py"
    with fsspec.open(uri, "rb") as f:
        data = f.read()
    with dst.open("wb") as f:
        f.write(data)


def _download_uri(dst_folder: PathType, uri: str):
    """Download ``uri`` by trying all downloaders on ``uri`` until one works."""
    dst_folder = Path(dst_folder)
    for processor in downloaders.values():
        try:
            processor(dst_folder, uri)
            break
        except NonMatchingURI:
            pass
    else:
        _download_generic(dst_folder, uri)


def _verify_files(folder: PathType):
    """Sanity checks downloaded files.

    Currently just checks if ".py" files are valid python code.
    """
    folder = Path(folder)
    for f in folder.rglob("*"):
        if f.suffix == ".py":
            code = f.read_text()
            ast.parse(code)


def _sha256sum(path: PathType):
    path = Path(path)
    h = hashlib.sha256()
    mv = memoryview(bytearray(128 * 1024))
    with path.open("rb", buffering=0) as f:
        while n := f.readinto(mv):
            h.update(mv[:n])
    return h.hexdigest()


def _sync(src_folder: PathType, dst_folder: PathType) -> bool:
    """Make ``dst_folder`` have the same contents as ``src_folder``.

    Returns
    -------
    bool
        ``True`` if contents of ``dst`` have changed; ``False`` otherwise.
    """
    changed = False
    src_folder, dst_folder = Path(src_folder), Path(dst_folder)

    src_files = {x.relative_to(src_folder) for x in src_folder.rglob("*")}
    dst_files = {x.relative_to(dst_folder) for x in dst_folder.rglob("*")}

    common_files = src_files.intersection(dst_files)
    src_only_files = src_files - dst_files
    dst_only_files = dst_files - src_files

    # compare common files and copy over on change
    for f in common_files:
        src = src_folder / f
        dst = dst_folder / f

        if _sha256sum(src) != _sha256sum(dst):
            changed = True
            shutil.copy(src, dst)

    # copy over src_only_files
    for f in src_only_files:
        changed = True
        src = src_folder / f
        dst = dst_folder / f
        shutil.copy(src, dst)

    # Remove files that only exist in the destination
    for f in dst_only_files:
        changed = True
        dst = dst_folder / f
        (dst_folder / f).unlink()

    return changed
