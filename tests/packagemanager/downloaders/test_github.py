import pytest

from belay.packagemanager import downloaders
from belay.packagemanager.downloaders._github import _parse_github_url


def test_parse_github_url_single_file():
    assert _parse_github_url(
        "https://github.com/BrianPugh/belay/blob/main/belay/__init__.py"
    ) == ("BrianPugh", "belay", "main", "belay/__init__.py")


def test_parse_github_url_subfolder():
    assert _parse_github_url("https://github.com/BrianPugh/belay/blob/main/docs/") == (
        "BrianPugh",
        "belay",
        "main",
        "docs/",
    )
    assert _parse_github_url("https://github.com/BrianPugh/belay/blob/main/docs") == (
        "BrianPugh",
        "belay",
        "main",
        "docs",
    )


def test_parse_github_url_githubusercontent():
    assert _parse_github_url(
        "https://raw.githubusercontent.com/BrianPugh/belay/main/belay/__init__.py"
    ) == ("BrianPugh", "belay", "main", "belay/__init__.py")


@pytest.mark.network
def test_download_github_folder(mocker, tmp_path):
    mocker.patch(
        "belay.project.find_cache_folder", return_value=tmp_path / ".belay-cache"
    )

    dst_path = tmp_path / "dst"

    uri = "https://github.com/BrianPugh/belay/tree/main/tests/github_download_folder"
    downloaders.github(dst_path, uri)

    assert (dst_path / "__init__.py").exists()
    assert (
        dst_path / "file1.py"
    ).read_text() == 'print("belay test file for downloading.")\n'
    assert (
        dst_path / "file2.txt"
    ).read_text() == "File for testing non-python downloads.\n"
    assert (dst_path / "submodule" / "__init__.py").exists()
    assert (
        dst_path / "submodule" / "sub1.py"
    ).read_text() == 'foo = "testing recursive download abilities."\n'


@pytest.mark.network
def test_download_github_single(tmp_path):
    uri = "https://github.com/BrianPugh/belay/blob/main/tests/github_download_folder/file1.py"
    downloaders.github(tmp_path, uri)

    assert (
        tmp_path / "file1.py"
    ).read_text() == 'print("belay test file for downloading.")\n'
