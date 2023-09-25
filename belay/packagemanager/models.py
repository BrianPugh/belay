import tomli
import cattrs
from attrs import frozen, field
from typing import List, Dict, Optional, Union, Any
from pathlib import Path

from belay.packagemanager.group import Group, DependencySource


converter = cattrs.Converter(forbid_extra_keys=True)


@frozen
class BelayConfig:  # TODO: Done
    """Configuration schema under the ``tool.belay`` section of ``pyproject.toml``."""

    # Name/Folder of project's primary micropython code.
    name: Optional[str] = None

    # Items in project directory to ignore.
    ignore: List[Path] = field(factory=list)

    # "main" dependencies
    dependencies: Dict[str, List[DependencySource]] = field(factory=dict)

    # Path to where dependency groups should be stored relative to project's root.
    dependencies_path: Path = Path(".belay/dependencies")

    #dependencies: List[Dependency]
    group: Dict[str, Group] = field(factory=dict)

    @group.validator  # pyright: ignore[reportGeneralTypeIssues]
    def _validator_main_not_in_group(self, _, value):
        if "main" in value:
            raise ValueError(
                'Specify "main" group dependencies under "tool.belay.dependencies", '
                'not "tool.belay.group.main.dependencies"'
            )

    @group.validator  # pyright: ignore[reportGeneralTypeIssues]
    def _validator_group_name_is_python_identifier(self, _, groups):
        for group_name in groups:
            if not group_name.isidentifier():
                raise ValueError("Dependency group name must be a valid python identifier.")

    @classmethod
    def from_pyproject(cls, path: Path) -> "BelayConfig":
        """Instantiate a BelayConfig object from a pyproject.toml.
        """
        with path.open("rb") as f:
            toml = tomli.load(f)
        unstructured_data = toml.get("tool", {}).get("belay", {})
        return converter.structure(unstructured_data, cls)


def _dependencies_preprocessor(
    dependencies: Dict[str, Union[str, List, Dict]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Preprocess unstructured dependency data.

    * ``str`` -> single dependency that may get renamed to __init__.py, if appropriate.
    * ``list`` -> list of dependencies. If an element is a str, it will not
      get renamed to __init__.py.
    * ``dict`` -> full dependency specification.
    """
    out = {}
    for dependency_name, dependency_values in dependencies.items():
        if isinstance(dependency_values, str):
            dependency_values = [
                {
                    "uri": dependency_values,
                    "rename_to_init": True,
                }
            ]
        elif isinstance(dependency_values, list):
            group_value_out = []
            for elem in dependency_values:
                if isinstance(elem, str):
                    group_value_out.append(
                        {
                            "uri": elem,
                        }
                    )
                elif isinstance(elem, list):
                    raise TypeError("Cannot have double nested lists in dependency specification.")
                elif isinstance(elem, (dict, DependencySource)):
                    group_value_out.append(elem)
                else:
                    raise NotImplementedError
            dependency_values = group_value_out
        elif isinstance(dependency_values, dict):
            dependency_values = dependency_values.copy()
            dependency_values.setdefault("rename_to_init", True)
            dependency_values = [dependency_values]
        elif isinstance(dependency_values, DependencySource):
            # Nothing to do
            pass
        else:
            raise TypeError

        out[dependency_name] = dependency_values

    return out


def _structure_group_config(data: dict, cl: type):
    if 'dependencies' in data:
        if not isinstance(data["dependencies"], dict):
            raise TypeError
        normalized_unstructured_dependencies = _dependencies_preprocessor(data["dependencies"])
        data['dependencies'] = {
            key: [converter.structure(dep, DependencySource) for dep in value]
            for key, value in normalized_unstructured_dependencies.items()
        }

    if "name" in data:
        raise ValueError(f"Cannot specify group name as an explicit 'name' field.")

    return cl(**data)


converter.register_structure_hook(Group, _structure_group_config)
#converter.register_structure_hook(BelayConfig, _structure_group_config)
