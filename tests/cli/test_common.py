import os

import pytest

from belay.cli.common import find_pyproject, load_pyproject, load_toml


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
