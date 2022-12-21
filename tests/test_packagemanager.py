import pytest
from typer.testing import CliRunner

import belay.packagemanager
from belay.packagemanager import Group


@pytest.fixture(autouse=True)
def tmp_path_find_dependencies_folder(tmp_path, mocker):
    mocker.patch("belay.project.find_dependencies_folder", return_value=tmp_path)


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


def test_download_all(main_group, mocker, spy_ast):
    _get_text = mocker.patch(
        "belay.packagemanager._get_text",
        side_effect=[
            "def foo(): return 0",
            "def bar(): return 1",
        ],
    )
    main_group.download()

    _get_text.assert_has_calls(
        [
            mocker.call("foo_url/foo.py"),
            mocker.call("bar_url/bar.py"),
        ]
    )
    assert spy_ast.parse.mock_calls == [
        mocker.call("def foo(): return 0"),
        mocker.call("def bar(): return 1"),
    ]

    actual_content = (main_group.folder / "foo.py").read_text()
    assert actual_content == "def foo(): return 0"

    actual_content = (main_group.folder / "bar.py").read_text()
    assert actual_content == "def bar(): return 1"


def test_download_specific(main_group, mocker, tmp_path, spy_ast):
    _get_text = mocker.patch(
        "belay.packagemanager._get_text",
        side_effect=[
            "def bar(): return 1",
        ],
    )

    main_group.download(packages=["bar"])

    _get_text.assert_called_once_with("bar_url/bar.py")
    spy_ast.parse.assert_called_once_with("def bar(): return 1")

    actual_content = (main_group.folder / "bar.py").read_text()
    assert actual_content == "def bar(): return 1"


@pytest.fixture
def main_group():
    return Group(
        name="main",
        dependencies={
            "foo": "foo_url/foo.py",
            "bar": "bar_url/bar.py",
        },
    )


def test_group_clean(main_group):
    main_group.folder.mkdir()
    (main_group.folder / "foo.py").touch()
    (main_group.folder / "baz.py").touch()

    main_group.clean()

    assert (main_group.folder / "foo.py").exists()
    assert not (main_group.folder / "baz.py").exists()
