import importlib.resources as importlib_resources
import re
import shutil
from pathlib import Path

import tomlkit
from packaging.utils import canonicalize_name

# Path for belay dependencies used in pytest pythonpath
BELAY_DEPENDENCIES_PATH = ".belay/dependencies/main"


def new(path: str = "."):
    """Create a new micropython project structure.

    If ``pyproject.toml`` already exists, adds the following sections:

    - ``[tool.belay]`` with project name derived from directory name.
    - ``[tool.belay.dependencies]`` for specifying micropython dependencies.
    - ``[tool.pytest.ini_options]`` with ``pythonpath`` including
      ``.belay/dependencies/main`` for test imports.

    Parameters
    ----------
    path : str
        Path to create the project at.
        Defaults to current directory.
    """
    dst_dir = Path(path).resolve()
    pyproject_path = dst_dir / "pyproject.toml"

    # Derive package name from directory name
    package_name = canonicalize_name(dst_dir.name)

    if pyproject_path.exists():
        # Existing project - add belay sections to pyproject.toml
        _add_belay_to_existing_pyproject(pyproject_path, package_name)
    else:
        # New project - copy full template
        _create_new_project(dst_dir, package_name)


def _add_belay_to_existing_pyproject(pyproject_path: Path, package_name: str):
    """Add belay configuration sections to an existing pyproject.toml."""
    content = pyproject_path.read_text(encoding="utf-8")
    doc = tomlkit.parse(content)

    # Ensure [tool] table exists
    if "tool" not in doc:
        doc["tool"] = tomlkit.table()

    tool = doc["tool"]

    # Check if belay is already configured
    if "belay" in tool:
        raise ValueError(
            f"Belay is already configured in {pyproject_path}. " "Remove [tool.belay] section to reinitialize."
        )

    # Add [tool.belay] section
    belay_table = tomlkit.table()
    belay_table["name"] = package_name
    tool["belay"] = belay_table

    # Add [tool.belay.dependencies] section
    tool["belay"]["dependencies"] = tomlkit.table()

    # Add or update [tool.pytest.ini_options] with pythonpath
    if "pytest" not in tool:
        tool["pytest"] = tomlkit.table()
    if "ini_options" not in tool["pytest"]:
        tool["pytest"]["ini_options"] = tomlkit.table()

    pytest_ini = tool["pytest"]["ini_options"]
    if "pythonpath" in pytest_ini:
        # Add BELAY_DEPENDENCIES_PATH if not already present
        existing = pytest_ini["pythonpath"]
        if isinstance(existing, str) and BELAY_DEPENDENCIES_PATH not in existing.split():
            pytest_ini["pythonpath"] = [existing, BELAY_DEPENDENCIES_PATH]
        elif isinstance(existing, list) and BELAY_DEPENDENCIES_PATH not in existing:
            existing.append(BELAY_DEPENDENCIES_PATH)
    else:
        pytest_ini["pythonpath"] = BELAY_DEPENDENCIES_PATH

    pyproject_path.write_text(tomlkit.dumps(doc), encoding="utf-8")


def _create_new_project(dst_dir: Path, package_name: str):
    """Create a new project from template."""
    template_dir = importlib_resources.files("belay") / "cli" / "new_template"

    if dst_dir.exists():
        # Directory exists (e.g., current directory), copy contents into it
        for item in Path(str(template_dir)).iterdir():
            if item.name in ("__pycache__",) or item.suffix == ".pyc":
                continue
            dst_item = dst_dir / item.name
            if item.is_dir():
                shutil.copytree(str(item), str(dst_item), ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))
            else:
                shutil.copy2(str(item), str(dst_item))
    else:
        # Create new directory
        shutil.copytree(str(template_dir), str(dst_dir), ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))

    # Find/Replace Engine
    replacements: dict[str, str] = {
        "packagename": package_name,
    }

    paths = list(dst_dir.rglob("*"))

    def replace(string):
        """Replace whole words only."""

        def _replace(match):
            return replacements[match.group(0)]

        pattern = "|".join(rf"\b{re.escape(s)}\b" if " " not in s else re.escape(s) for s in replacements)
        return re.sub(pattern, _replace, string)

    for path in paths:
        if path.is_dir():
            continue

        contents = path.read_text(encoding="utf-8")
        contents = replace(contents)
        path.write_text(contents)
        if path.stem in replacements:
            dst = path.with_name(replacements[path.stem] + path.suffix)
            path.replace(dst)

    # Move the app folder
    (dst_dir / "packagename").replace(dst_dir / replacements["packagename"])
