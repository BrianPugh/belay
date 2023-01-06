import pytest

import belay.packagemanager
from belay.packagemanager import Group


@pytest.fixture(autouse=True)
def tmp_path_find_dependencies_folder(tmp_path, mocker):
    dependencies_folder = tmp_path / ".belay" / "dependencies"
    dependencies_folder.mkdir(parents=True)
    mocker.patch(
        "belay.project.find_dependencies_folder",
        return_value=dependencies_folder,
    )


@pytest.fixture
def spy_ast(mocker):
    return mocker.spy(belay.packagemanager, "ast")


@pytest.fixture
def main_group(tmp_path):
    foo_path = tmp_path / "foo_url" / "foo.py"
    foo_path.parent.mkdir(parents=True)
    foo_path.write_text("def foo(): return 0")

    bar_path = tmp_path / "bar_url" / "bar.py"
    bar_path.parent.mkdir(parents=True)
    bar_path.write_text("def bar(): return 1")

    return Group(
        name="main",
        dependencies={
            "foo": str(foo_path),
            "bar": str(bar_path),
        },
    )


@pytest.mark.network
def test_download_github_folder(tmp_path):
    uri = "https://github.com/BrianPugh/belay/tree/main/tests/github_download_folder"
    belay.packagemanager._download_github(tmp_path, uri)

    assert (tmp_path / "__init__.py").exists()
    assert (
        tmp_path / "file1.py"
    ).read_text() == 'print("belay test file for downloading.")\n'
    assert (
        tmp_path / "file2.txt"
    ).read_text() == "File for testing non-python downloads.\n"
    assert (tmp_path / "submodule" / "__init__.py").exists()
    assert (
        tmp_path / "submodule" / "sub1.py"
    ).read_text() == 'foo = "testing recursive download abilities."\n'


@pytest.mark.network
def test_download_github_single(tmp_path):
    uri = "https://github.com/BrianPugh/belay/blob/main/tests/github_download_folder/file1.py"
    belay.packagemanager._download_github(tmp_path, uri)

    assert (
        tmp_path / "__init__.py"
    ).read_text() == 'print("belay test file for downloading.")\n'


def test_download_all(main_group, mocker, spy_ast):
    main_group.download()

    assert spy_ast.parse.mock_calls == [
        mocker.call("def foo(): return 0"),
        mocker.call("def bar(): return 1"),
    ]

    actual_content = (main_group.folder / "foo" / "__init__.py").read_text()
    assert actual_content == "def foo(): return 0"

    actual_content = (main_group.folder / "bar" / "__init__.py").read_text()
    assert actual_content == "def bar(): return 1"


def test_download_specific(main_group, spy_ast):
    main_group.download(packages=["bar"])

    spy_ast.parse.assert_called_once_with("def bar(): return 1")

    actual_content = (main_group.folder / "bar" / "__init__.py").read_text()
    assert actual_content == "def bar(): return 1"


def test_group_clean(main_group):
    main_group.folder.mkdir()
    (main_group.folder / "foo.py").touch()
    (main_group.folder / "baz.py").touch()

    main_group.clean()

    assert (main_group.folder / "foo.py").exists()
    assert not (main_group.folder / "baz.py").exists()
