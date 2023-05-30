import pytest

from belay.packagemanager import downloaders


@pytest.mark.network
def test_download_github_folder(mocker, tmp_path):
    mocker.patch("belay.project.find_cache_folder", return_value=tmp_path / ".belay-cache")

    dst_path = tmp_path / "dst"

    uri = "https://github.com/BrianPugh/belay/tree/main/tests/github_download_folder"
    downloaders.github(dst_path, uri)

    assert (dst_path / "__init__.py").exists()
    assert (dst_path / "file1.py").read_text() == 'print("belay test file for downloading.")\n'
    assert (dst_path / "file2.txt").read_text() == "File for testing non-python downloads.\n"
    assert (dst_path / "submodule" / "__init__.py").exists()
    assert (dst_path / "submodule" / "sub1.py").read_text() == 'foo = "testing recursive download abilities."\n'


@pytest.mark.network
def test_download_github_single(tmp_path):
    uri = "https://github.com/BrianPugh/belay/blob/main/tests/github_download_folder/file1.py"
    downloaders.github(tmp_path, uri)

    assert (tmp_path / "file1.py").read_text() == 'print("belay test file for downloading.")\n'
