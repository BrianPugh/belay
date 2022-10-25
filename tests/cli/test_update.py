import pytest
from typer.testing import CliRunner

import belay.cli.update
from belay.cli import app

cli_runner = CliRunner()


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
    out = belay.cli.update._process_url_github(url)
    assert (
        out
        == "https://raw.githubusercontent.com/BrianPugh/belay/main/belay/__init__.py"
    )


def test_process_url():
    actual = belay.cli.update._process_url(
        "http://github.com/BrianPugh/belay/blob/main/belay/__init__.py"
    )
    assert (
        actual
        == "https://raw.githubusercontent.com/BrianPugh/belay/main/belay/__init__.py"
    )


def test_download_dependencies(mocker, tmp_path):
    _get_text = mocker.patch(
        "belay.cli.update._get_text", return_value="def foo(): return 0"
    )
    spy_ast = mocker.spy(belay.cli.update, "ast")

    belay.cli.update._download_dependencies(
        {
            "foo": "foo.py",
        },
        local_dir=tmp_path,
    )

    _get_text.assert_called_once_with("foo.py")
    spy_ast.parse.assert_called_once_with("def foo(): return 0")

    actual_content = (tmp_path / "foo.py").read_text()
    assert actual_content == "def foo(): return 0"
