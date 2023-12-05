import os

import pytest

from belay.cli._clean import clean
from belay.packagemanager import Group


@pytest.fixture
def project_folder(tmp_path):
    (tmp_path / ".belay").mkdir()
    (tmp_path / ".belay" / "dependencies").mkdir()
    (tmp_path / ".belay" / "dependencies" / "dev").mkdir()
    (tmp_path / ".belay" / "dependencies" / "dev" / "bar").touch()
    (tmp_path / ".belay" / "dependencies" / "dev" / "baz").touch()
    (tmp_path / ".belay" / "dependencies" / "main").mkdir()
    (tmp_path / ".belay" / "dependencies" / "main" / "foo").touch()

    (tmp_path / "pyproject.toml").touch()

    os.chdir(tmp_path)

    return tmp_path


def test_clean_basic(project_folder, mocker):
    groups = [
        Group("main", dependencies={"foo": "foo_uri"}),
        Group("dev", dependencies={"bar": "bar_uri"}),
    ]
    mocker.patch("belay.cli._clean.load_groups", return_value=groups)

    dependencies_folder = project_folder / ".belay" / "dependencies"

    clean()

    assert (dependencies_folder / "main" / "foo").exists()

    assert (dependencies_folder / "dev").exists()
    assert (dependencies_folder / "dev" / "bar").exists()
    assert not (dependencies_folder / "dev" / "baz").exists()


def test_clean_missing_group(project_folder, mocker):
    groups = [
        Group("main", dependencies={"foo": "foo_uri"}),
    ]
    mocker.patch("belay.cli._clean.load_groups", return_value=groups)

    dependencies_folder = project_folder / ".belay" / "dependencies"

    clean()

    assert (dependencies_folder / "main" / "foo").exists()

    assert not (dependencies_folder / "dev").exists()
