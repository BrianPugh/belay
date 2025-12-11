import pytest

from belay.packagemanager.downloaders import GitLabUrl, GitProviderUrl


@pytest.mark.network
def test_download_gitlab_single(tmp_path):
    """Test downloading a single file from GitLab using full URL."""
    uri = "https://gitlab.com/pages/plain-html/-/blob/main/public/index.html"
    parsed = GitProviderUrl.parse(uri)
    assert isinstance(parsed, GitLabUrl)
    parsed.download(tmp_path)

    content = (tmp_path / "index.html").read_text()
    assert "<!DOCTYPE html>" in content
    assert "Hello World!" in content


@pytest.mark.network
def test_download_gitlab_single_raw(tmp_path):
    """Test downloading a single file from GitLab using raw URL."""
    uri = "https://gitlab.com/pages/plain-html/-/raw/main/public/index.html"
    parsed = GitProviderUrl.parse(uri)
    assert isinstance(parsed, GitLabUrl)
    parsed.download(tmp_path)

    content = (tmp_path / "index.html").read_text()
    assert "<!DOCTYPE html>" in content
    assert "Hello World!" in content


@pytest.mark.network
def test_download_gitlab_folder(mocker, tmp_path):
    """Test downloading a folder from GitLab using full URL."""
    mocker.patch("belay.project.find_cache_folder", return_value=tmp_path / ".belay-cache")

    dst_path = tmp_path / "dst"

    uri = "https://gitlab.com/pages/plain-html/-/tree/main/public"
    parsed = GitProviderUrl.parse(uri)
    assert isinstance(parsed, GitLabUrl)
    parsed.download(dst_path)

    assert (dst_path / "index.html").exists()
    content = (dst_path / "index.html").read_text()
    assert "Hello World!" in content


@pytest.mark.network
def test_download_gitlab_shorthand_single(tmp_path):
    """Test downloading a single file using gitlab: shorthand."""
    uri = "gitlab:pages/plain-html/public/index.html@main"
    parsed = GitProviderUrl.parse(uri)
    assert isinstance(parsed, GitLabUrl)
    parsed.download(tmp_path)

    content = (tmp_path / "index.html").read_text()
    assert "<!DOCTYPE html>" in content
    assert "Hello World!" in content


@pytest.mark.network
def test_download_gitlab_shorthand_folder(mocker, tmp_path):
    """Test downloading a folder using gitlab: shorthand."""
    mocker.patch("belay.project.find_cache_folder", return_value=tmp_path / ".belay-cache")

    dst_path = tmp_path / "dst"

    uri = "gitlab:pages/plain-html/public@main"
    parsed = GitProviderUrl.parse(uri)
    assert isinstance(parsed, GitLabUrl)
    parsed.download(dst_path)

    assert (dst_path / "index.html").exists()
    content = (dst_path / "index.html").read_text()
    assert "Hello World!" in content
