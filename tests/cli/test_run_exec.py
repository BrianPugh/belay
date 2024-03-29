import os

import pytest

from belay.cli.main import run_exec


@pytest.fixture
def project_dir(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        """
    [tool.belay.dependencies]
    foo = "foo_uri"

    [tool.belay.group.dev.dependencies]
    bar = "bar_uri"
    """
    )
    os.chdir(tmp_path)


def test_run_exec(project_dir, mocker):
    command = ["micropython", "-m", "module"]
    mock_run = mocker.patch("belay.cli.main.subprocess.run")
    run_exec(command)
    mock_run.assert_called_once_with(
        command,
        env=mocker.ANY,
        check=True,
    )
