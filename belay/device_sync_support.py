import subprocess
from pathlib import Path
from typing import Optional, Union

from pathspec import PathSpec
from pathspec.util import append_dir_sep

from ._minify import minify as minify_code
from .hash import fnv1a
from .typing import PathType


def discover_files_dirs(
    remote_dir: str,
    local_file_or_folder: Path,
    ignore: Optional[list] = None,
):
    src_objects = []
    if local_file_or_folder.is_dir():
        if ignore is None:
            ignore = []
        ignore_spec = PathSpec.from_lines("gitwildmatch", ignore)
        for src_object in local_file_or_folder.rglob("*"):
            if ignore_spec.match_file(append_dir_sep(src_object)):
                continue
            src_objects.append(src_object)
        # Sort so that folder creation comes before file sending.
        src_objects.sort()

        src_files, src_dirs = [], []
        for src_object in src_objects:
            if src_object.is_dir():
                src_dirs.append(src_object)
            else:
                src_files.append(src_object)
        dst_files = [remote_dir / src.relative_to(local_file_or_folder) for src in src_files]
    else:
        src_files = [local_file_or_folder]
        src_dirs = []
        dst_files = [Path(remote_dir) / local_file_or_folder.name]

    return src_files, src_dirs, dst_files


def preprocess_keep(
    keep: Union[None, list, str, bool],
    dst: str,
) -> list:
    if keep is None:
        keep = ["boot.py", "webrepl_cfg.py", "lib"] if dst == "/" else []
    elif isinstance(keep, str):
        keep = [keep]
    elif isinstance(keep, (list, tuple)):
        pass
    elif isinstance(keep, bool):
        keep = []
    else:
        raise TypeError
    keep = [(dst / Path(x)).as_posix() for x in keep]
    return keep


def preprocess_ignore(ignore: Union[None, str, list, tuple]) -> list:
    if ignore is None:
        ignore = ["*.pyc", "__pycache__", ".DS_Store", ".pytest_cache"]
    elif isinstance(ignore, str):
        ignore = [ignore]
    elif isinstance(ignore, (list, tuple)):
        ignore = list(ignore)
    else:
        raise TypeError
    return ignore


def preprocess_src_file(
    tmp_dir: PathType,
    src_file: PathType,
    minify: bool,
    mpy_cross_binary: Union[str, Path, None],
) -> Path:
    tmp_dir = Path(tmp_dir)
    src_file = Path(src_file)

    transformed = tmp_dir / src_file.relative_to(src_file.anchor) if src_file.is_absolute() else tmp_dir / src_file
    transformed.parent.mkdir(parents=True, exist_ok=True)

    if src_file.suffix == ".py":
        if mpy_cross_binary:
            transformed = transformed.with_suffix(".mpy")
            subprocess.check_output([mpy_cross_binary, "-o", transformed, src_file])  # nosec
            return transformed
        elif minify:
            minified = minify_code(src_file.read_text())
            transformed.write_text(minified)
            return transformed

    return src_file


def preprocess_src_file_hash(*args, **kwargs):
    src_file = preprocess_src_file(*args, **kwargs)
    src_hash = fnv1a(src_file)
    return src_file, src_hash


def generate_dst_dirs(dst, src, src_dirs) -> list:
    dst_dirs = [(dst / x.relative_to(src)).as_posix() for x in src_dirs]
    # Add all directories leading up to ``dst``.
    dst_prefix_tokens = dst.split("/")
    for i in range(2, len(dst_prefix_tokens) + (dst[-1] != "/")):
        dst_dirs.append("/".join(dst_prefix_tokens[:i]))
    dst_dirs.sort()
    return dst_dirs
