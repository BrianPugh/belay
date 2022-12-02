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


@pytest.mark.parametrize(
    "url, formatted",
    [
        (
            "http://github.com/BrianPugh/belay/blob/main/belay/__init__.py",
            "https://raw.githubusercontent.com/BrianPugh/belay/main/belay/__init__.py",
        ),
        ("path/to/local/file.py", "path/to/local/file.py"),
    ],
)
def test_process_url(url, formatted):
    actual = belay.packagemanager._process_url(url)
    assert actual == formatted


@pytest.fixture
def spy_ast(mocker):
    return mocker.spy(belay.packagemanager, "ast")


@pytest.fixture
def mock_httpx(mocker):
    mock_httpx = mocker.patch("belay.packagemanager.httpx")
    mock_httpx.get.return_value = mocker.MagicMock()
    return mock_httpx


@pytest.mark.parametrize("url", ["https://foo.com", "http://foo.com"])
def test_get_text_url(mock_httpx, url):
    res = belay.packagemanager._get_text(url)
    mock_httpx.get.assert_called_once_with(url)
    mock_httpx.get.return_value.raise_for_status.assert_called_once()
    assert res == mock_httpx.get.return_value.text


def test_get_text_local(tmp_path):
    fn = tmp_path / "foo.py"
    fn.write_text("bar")

    res = belay.packagemanager._get_text(fn)
    assert res == "bar"

    res = belay.packagemanager._get_text(str(fn))
    assert res == "bar"


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
        tmp_path,
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
        tmp_path,
        packages=["bar"],
    )

    assert _get_text.mock_calls == [
        mocker.call("bar.py"),
    ]
    assert spy_ast.parse.mock_calls == [
        mocker.call("def bar(): return 1"),
    ]

    actual_content = (tmp_path / "bar.py").read_text()
    assert actual_content == "def bar(): return 1"


def test_clean_local(tmp_path):
    dependencies = ["foo", "bar"]
    (tmp_path / "foo.py").touch()
    (tmp_path / "baz.py").touch()

    belay.packagemanager.clean_local(dependencies=dependencies, local_dir=tmp_path)

    assert (tmp_path / "foo.py").exists()
    assert not (tmp_path / "baz.py").exists()
