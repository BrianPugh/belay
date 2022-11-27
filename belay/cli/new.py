import importlib.resources as pkg_resources
import re
import shutil
from pathlib import Path

from packaging.utils import canonicalize_name
from typer import Argument, Option


def new(project_name: str = Argument(..., help="Project Name.")):
    """Create a new micropython project structure."""
    package_name = canonicalize_name(project_name)
    dst_dir = Path() / project_name
    template_dir = pkg_resources.files("belay") / "cli" / "new_template"

    shutil.copytree(str(template_dir), str(dst_dir))

    # Find/Replace Engine
    replacements: dict[str, str] = {
        "packagename": package_name,
    }

    paths = list(dst_dir.rglob("*"))

    def replace(string):
        """Replace whole words only."""

        def _replace(match):
            return replacements[match.group(0)]

        return re.sub(
            "|".join(r"\b%s\b" % re.escape(s) for s in replacements), _replace, string
        )

    for path in paths:
        if path.is_dir():
            continue

        contents = path.read_text()
        contents = replace(contents)
        path.write_text(contents)
        if path.stem in replacements:
            dst = path.with_name(replacements[path.stem] + path.suffix)
            path.replace(dst)

    # Move the app folder
    (dst_dir / "packagename").replace(dst_dir / replacements["packagename"])
