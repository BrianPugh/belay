import pytest

import belay.packagemanager
from belay.packagemanager.group import Group, _verify_files


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
    return mocker.spy(belay.packagemanager.group, "ast")


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
    (main_group.folder / "foo").mkdir()
    (main_group.folder / "baz").mkdir()

    main_group.clean()

    assert (main_group.folder / "foo").exists()
    assert not (main_group.folder / "baz").exists()


def test_verify_files_micropython_viper(tmp_path):
    code_path = tmp_path / "code.py"
    code_path.write_text(
        """
@micropython.viper
def foo(self, arg: int) -> int:
    buf = ptr8(self.linebuf) # self.linebuf is a bytearray or bytes object
    for x in range(20, 30):
        bar = buf[x] # Access a data item through the pointer
"""
    )
    _verify_files(code_path)
