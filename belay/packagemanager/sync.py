import hashlib
import shutil
from pathlib import Path

from belay.typing import PathType


def _sha256sum(path: PathType):
    path = Path(path)
    h = hashlib.sha256()
    mv = memoryview(bytearray(128 * 1024))
    with path.open("rb", buffering=0) as f:
        while n := f.readinto(mv):
            h.update(mv[:n])
    return h.hexdigest()


def sync(src_folder: PathType, dst_folder: PathType) -> bool:
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
