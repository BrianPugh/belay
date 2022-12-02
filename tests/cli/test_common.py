import os

import pytest

import belay
from belay.cli.common import (
    find_pyproject,
    load_dependency_groups,
    load_pyproject,
    load_toml,
)


@pytest.fixture
def toml_file_standard(tmp_path):
    fn = tmp_path / "pyproject.toml"
    fn.write_text(
        """
[tool.belay]
foo = "bar"
"""
    )
    return fn


def test_load_toml_standard(toml_file_standard):
    actual = load_toml(toml_file_standard)
    assert actual == {"foo": "bar"}


def test_find_pyproject_parents(tmp_path, toml_file_standard):
    fn = tmp_path / "folder1" / "folder2" / "folder3" / "pyproject.toml"
    fn.parent.mkdir(exist_ok=True, parents=True)
    os.chdir(fn.parent)

    actual = find_pyproject()
    assert actual == toml_file_standard

    actual = load_pyproject()
    assert actual == {"foo": "bar"}


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
def mock_load_pyproject(mocker):
    return mocker.patch("belay.cli.common.load_pyproject")


def test_load_dependency_groups_empty(mock_load_pyproject):
    mock_load_pyproject.return_value = {}
    assert load_dependency_groups() == {}


def test_load_dependency_groups_main_only(mock_load_pyproject):
    mock_load_pyproject.return_value = {
        "dependencies": {"foo": "foo_uri"},
    }
    assert load_dependency_groups() == {
        "main": {"foo": "foo_uri"},
    }


def test_load_dependency_groups_main_group(mock_load_pyproject):
    mock_load_pyproject.return_value = {
        "group": {
            "main": {
                "dependencies": {
                    "foo": "foo_uri",
                }
            },
        },
    }
    with pytest.raises(belay.ConfigError):
        load_dependency_groups()


def test_load_dependency_groups_multiple(mock_load_pyproject):
    mock_load_pyproject.return_value = {
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
    assert load_dependency_groups() == {
        "main": {"foo": "foo_uri"},
        "dev": {"bar": "bar_uri"},
    }
