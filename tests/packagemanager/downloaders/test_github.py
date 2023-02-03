import pytest

from belay.packagemanager import downloaders


@pytest.mark.network
def test_download_github_folder(tmp_path):
    uri = "https://github.com/BrianPugh/belay/tree/main/tests/github_download_folder"
    downloaders.github(tmp_path, uri)

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
    downloaders.github(tmp_path, uri)

    assert (
        tmp_path / "__init__.py"
    ).read_text() == 'print("belay test file for downloading.")\n'
