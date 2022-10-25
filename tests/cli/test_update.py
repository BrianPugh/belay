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
