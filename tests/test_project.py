import pytest
from pydantic import ValidationError

from belay.packagemanager import Group
from belay.project import find_pyproject, load_groups, load_pyproject, load_toml


@pytest.fixture
def toml_file_standard(tmp_path):
    fn = tmp_path / "pyproject.toml"
    fn.write_text(
        """
[tool.belay]
name = "bar"
"""
    )
    return fn


def test_load_toml_standard(toml_file_standard):
    actual = load_toml(toml_file_standard)
    assert actual == {"name": "bar"}


def test_find_pyproject_parents(tmp_cwd, toml_file_standard, monkeypatch):
    fn = tmp_cwd / "folder1" / "folder2" / "folder3" / "pyproject.toml"
    fn.parent.mkdir(exist_ok=True, parents=True)
    monkeypatch.chdir(fn.parent)

    actual = find_pyproject()
    assert actual == toml_file_standard

    actual = load_pyproject()
    assert actual.name == "bar"


def test_load_toml_no_belay_section(tmp_path):
    fn = tmp_path / "pyproject.toml"
    fn.write_text(
        """
[not_belay]
foo = "bar"
"""
    )
    actual = load_toml(fn)
    assert not actual


@pytest.fixture
def mock_load_toml(mocker):
    return mocker.patch("belay.project.load_toml")


def test_load_dependency_groups_empty(mock_load_toml):
    mock_load_toml.return_value = {}
    assert load_groups() == [Group("main")]


def test_load_dependency_groups_main_only(mock_load_toml):
    mock_load_toml.return_value = {
        "dependencies": {"foo": "foo_uri"},
    }
    assert load_groups() == [
        Group("main", dependencies={"foo": "foo_uri"}),
    ]


def test_load_dependency_groups_main_group(mock_load_toml):
    mock_load_toml.return_value = {
        "group": {
            "main": {
                "dependencies": {
                    "foo": "foo_uri",
                }
            },
        },
    }
    with pytest.raises(ValidationError):
        load_groups()


def test_load_dependency_groups_multiple(mock_load_toml):
    mock_load_toml.return_value = {
        "dependencies": {"foo": "foo_uri"},
        "group": {
            "dev": {
                "dependencies": {
                    "bar": "bar_uri",
                }
            },
            "doc": {},  # This group doesn't have a "dependencies" field.
        },
    }
    assert load_groups() == [
        Group("dev", dependencies={"bar": "bar_uri"}),
        Group("doc", dependencies={}),
        Group("main", dependencies={"foo": "foo_uri"}),
    ]
