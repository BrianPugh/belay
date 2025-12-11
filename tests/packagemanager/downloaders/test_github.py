import pytest

from belay.packagemanager.downloaders import GitHubUrl, GitProviderUrl


@pytest.mark.network
def test_download_github_folder(mocker, tmp_path):
    mocker.patch("belay.project.find_cache_folder", return_value=tmp_path / ".belay-cache")

    dst_path = tmp_path / "dst"

    uri = "https://github.com/BrianPugh/belay/tree/main/tests/github_download_folder"
    parsed = GitProviderUrl.parse(uri)
    assert isinstance(parsed, GitHubUrl)
    parsed.download(dst_path)

    assert (dst_path / "__init__.py").exists()
    assert (dst_path / "file1.py").read_text() == 'print("belay test file for downloading.")\n'
    assert (dst_path / "file2.txt").read_text() == "File for testing non-python downloads.\n"
    assert (dst_path / "submodule" / "__init__.py").exists()
    assert (dst_path / "submodule" / "sub1.py").read_text() == 'foo = "testing recursive download abilities."\n'


@pytest.mark.network
def test_download_github_single(tmp_path):
    uri = "https://github.com/BrianPugh/belay/blob/main/tests/github_download_folder/file1.py"
    parsed = GitProviderUrl.parse(uri)
    assert isinstance(parsed, GitHubUrl)
    parsed.download(tmp_path)

    assert (tmp_path / "file1.py").read_text() == 'print("belay test file for downloading.")\n'


@pytest.mark.network
def test_download_github_shorthand_single(tmp_path):
    """Test downloading a single file using github: shorthand."""
    uri = "github:BrianPugh/belay/tests/github_download_folder/file1.py@main"
    parsed = GitProviderUrl.parse(uri)
    assert isinstance(parsed, GitHubUrl)
    parsed.download(tmp_path)

    assert (tmp_path / "file1.py").read_text() == 'print("belay test file for downloading.")\n'


@pytest.mark.network
def test_download_github_shorthand_folder(mocker, tmp_path):
    """Test downloading a folder using github: shorthand."""
    mocker.patch("belay.project.find_cache_folder", return_value=tmp_path / ".belay-cache")

    dst_path = tmp_path / "dst"

    uri = "github:BrianPugh/belay/tests/github_download_folder@main"
    parsed = GitProviderUrl.parse(uri)
    assert isinstance(parsed, GitHubUrl)
    parsed.download(dst_path)

    assert (dst_path / "__init__.py").exists()
    assert (dst_path / "file1.py").read_text() == 'print("belay test file for downloading.")\n'
    assert (dst_path / "file2.txt").read_text() == "File for testing non-python downloads.\n"
