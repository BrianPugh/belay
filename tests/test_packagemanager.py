import pytest
from typer.testing import CliRunner

import belay.packagemanager


@pytest.mark.parametrize("http", ["https://", "http://"])
@pytest.mark.parametrize("www", ["www.", ""])
@pytest.mark.parametrize(
    "body",
    [
        "github.com/BrianPugh/belay/blob/main/belay/__init__.py",
        "raw.githubusercontent.com/BrianPugh/belay/main/belay/__init__.py",
    ],
)
def test_process_url_github(http, www, body):
    url = http + www + body
    out = belay.packagemanager._process_url_github(url)
    assert (
        out
        == "https://raw.githubusercontent.com/BrianPugh/belay/main/belay/__init__.py"
    )


def test_process_url():
    actual = belay.packagemanager._process_url(
        "http://github.com/BrianPugh/belay/blob/main/belay/__init__.py"
    )
    assert (
        actual
        == "https://raw.githubusercontent.com/BrianPugh/belay/main/belay/__init__.py"
    )


@pytest.fixture
def spy_ast(mocker):
    return mocker.spy(belay.packagemanager, "ast")


def test_download_dependencies_all(mocker, tmp_path, spy_ast):
    _get_text = mocker.patch(
        "belay.packagemanager._get_text",
        side_effect=[
            "def foo(): return 0",
            "def bar(): return 1",
        ],
    )

    belay.packagemanager.download_dependencies(
        {
            "foo": "foo.py",
            "bar": "bar.py",
        },
        local_dir=tmp_path,
    )

    assert _get_text.mock_calls == [
        mocker.call("foo.py"),
        mocker.call("bar.py"),
    ]
    assert spy_ast.parse.mock_calls == [
        mocker.call("def foo(): return 0"),
        mocker.call("def bar(): return 1"),
    ]

    actual_content = (tmp_path / "foo.py").read_text()
    assert actual_content == "def foo(): return 0"

    actual_content = (tmp_path / "bar.py").read_text()
    assert actual_content == "def bar(): return 1"


def test_download_dependencies_specific(mocker, tmp_path, spy_ast):
    _get_text = mocker.patch(
        "belay.packagemanager._get_text",
        side_effect=[
            "def bar(): return 1",
        ],
    )

    belay.packagemanager.download_dependencies(
        {
            "foo": "foo.py",
            "bar": "bar.py",
        },
        packages=["bar"],
        local_dir=tmp_path,
    )

    assert _get_text.mock_calls == [
        mocker.call("bar.py"),
    ]
    assert spy_ast.parse.mock_calls == [
        mocker.call("def bar(): return 1"),
    ]

    actual_content = (tmp_path / "bar.py").read_text()
    assert actual_content == "def bar(): return 1"
