import pytest

from belay.packagemanager.downloaders import (
    GitHubUrl,
    GitLabUrl,
    GitProviderUrl,
    InvalidGitUrlError,
    rewrite_url,
)
from belay.packagemanager.downloaders.common import _download_generic


@pytest.mark.parametrize(
    "url,expected",
    [
        # GitHub shorthand
        (
            "github:user/repo/path/file.py@main",
            ("github", "user", "repo", "path/file.py", "main"),
        ),
        (
            "github:user/repo/path/file.py",
            ("github", "user", "repo", "path/file.py", "HEAD"),
        ),
        (
            "github:user/repo@v1.0",
            ("github", "user", "repo", "", "v1.0"),
        ),
        (
            "github:user/repo",
            ("github", "user", "repo", "", "HEAD"),
        ),
        # GitLab shorthand
        (
            "gitlab:user/repo/path/file.py@develop",
            ("gitlab", "user", "repo", "path/file.py", "develop"),
        ),
        (
            "gitlab:user/repo",
            ("gitlab", "user", "repo", "", "HEAD"),
        ),
        # GitHub full HTTPS URLs
        (
            "https://github.com/user/repo/blob/main/path/file.py",
            ("github", "user", "repo", "path/file.py", "main"),
        ),
        (
            "https://github.com/user/repo/tree/develop/src",
            ("github", "user", "repo", "src", "develop"),
        ),
        (
            "https://raw.githubusercontent.com/user/repo/v1.0/lib.py",
            ("github", "user", "repo", "lib.py", "v1.0"),
        ),
        # GitLab full HTTPS URLs
        (
            "https://gitlab.com/user/repo/-/blob/main/path/file.py",
            ("gitlab", "user", "repo", "path/file.py", "main"),
        ),
        (
            "https://gitlab.com/user/repo/-/tree/develop/src",
            ("gitlab", "user", "repo", "src", "develop"),
        ),
        (
            "https://gitlab.com/user/repo/-/raw/v1.0/lib.py",
            ("gitlab", "user", "repo", "lib.py", "v1.0"),
        ),
    ],
)
def test_git_provider_url_parse(url, expected):
    result = GitProviderUrl.parse(url)
    assert result is not None
    assert (result.scheme, result.user, result.repo, result.path, result.branch) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/file.py",
        "http://bitbucket.org/user/repo",  # Not supported yet
        "mip:aiohttp",
        "aiohttp",
        "",
    ],
)
def test_git_provider_url_parse_raises_for_unrecognized(url):
    with pytest.raises(InvalidGitUrlError):
        GitProviderUrl.parse(url)


def test_git_provider_url_parse_invalid_format_raises():
    with pytest.raises(ValueError, match="Invalid github URL"):
        GitProviderUrl.parse("github:onlyuser")


def test_git_provider_url_canonical_id():
    parsed = GitProviderUrl.parse("github:User/Repo/path@main")
    assert parsed.canonical_id == "user/repo"


def test_git_provider_url_scheme():
    """Test that scheme property returns correct provider identifier."""
    github_url = GitProviderUrl.parse("github:user/repo")
    assert github_url.scheme == "github"

    gitlab_url = GitProviderUrl.parse("gitlab:user/repo")
    assert gitlab_url.scheme == "gitlab"

    # Also works for HTTPS URLs
    github_https = GitProviderUrl.parse("https://github.com/user/repo/blob/main/file.py")
    assert github_https.scheme == "github"

    gitlab_https = GitProviderUrl.parse("https://gitlab.com/user/repo/-/blob/main/file.py")
    assert gitlab_https.scheme == "gitlab"


def test_git_provider_url_raw_url_github():
    parsed = GitProviderUrl.parse("github:user/repo/path/file.py@main")
    assert parsed.raw_url == "https://raw.githubusercontent.com/user/repo/main/path/file.py"

    # Without path
    parsed = GitProviderUrl.parse("github:user/repo@main")
    assert parsed.raw_url == "https://raw.githubusercontent.com/user/repo/main"


def test_git_provider_url_raw_url_gitlab():
    parsed = GitProviderUrl.parse("gitlab:user/repo/path/file.py@develop")
    assert parsed.raw_url == "https://gitlab.com/user/repo/-/raw/develop/path/file.py"


@pytest.mark.parametrize(
    "url,expected",
    [
        ("github:user/repo/file.py", True),
        ("github:user/repo/path/file.mpy", True),
        ("github:user/repo/package.json", True),
        ("github:user/repo/lib", False),  # No extension
        ("github:user/repo", False),  # No path
        ("github:user/repo/", False),  # Empty path
        ("github:user/repo/.github", False),  # Hidden directory (dot at start)
    ],
)
def test_git_provider_url_has_file_extension(url, expected):
    parsed = GitProviderUrl.parse(url)
    assert parsed.has_file_extension() == expected


def test_rewrite_url_uses_git_provider_url():
    """Test that rewrite_url correctly delegates to GitProviderUrl.parse."""
    assert rewrite_url("github:user/repo/file.py@main") == "https://raw.githubusercontent.com/user/repo/main/file.py"
    assert rewrite_url("gitlab:user/repo/file.py@dev") == "https://gitlab.com/user/repo/-/raw/dev/file.py"
    # Non-shorthand URLs pass through unchanged
    assert rewrite_url("https://example.com/file.py") == "https://example.com/file.py"


def test_git_provider_url_registry():
    """Test that subclasses are registered and discoverable."""
    # Verify registry contains expected providers
    assert set(GitProviderUrl.keys()) == {"github", "gitlab"}

    # Verify lookup returns correct classes
    assert GitProviderUrl["github"] is GitHubUrl
    assert GitProviderUrl["gitlab"] is GitLabUrl


def test_git_provider_url_returns_correct_subclass():
    """Test that parse() returns the correct subclass type."""
    # Shorthand URLs
    github_url = GitProviderUrl.parse("github:user/repo")
    assert isinstance(github_url, GitHubUrl)

    gitlab_url = GitProviderUrl.parse("gitlab:user/repo")
    assert isinstance(gitlab_url, GitLabUrl)

    # Full HTTPS URLs
    github_https = GitProviderUrl.parse("https://github.com/user/repo/blob/main/file.py")
    assert isinstance(github_https, GitHubUrl)

    gitlab_https = GitProviderUrl.parse("https://gitlab.com/user/repo/-/blob/main/file.py")
    assert isinstance(gitlab_https, GitLabUrl)


def test_download_generic_local_single(tmp_path):
    src = tmp_path / "src" / "foo.py"
    dst = tmp_path / "dst"

    src.parent.mkdir()
    dst.mkdir()

    src.write_text("a = 5")

    _download_generic(dst, str(src))

    assert (dst / "foo.py").read_text() == "a = 5"


def test_download_generic_local_folder(tmp_path):
    src_folder = tmp_path / "src"
    src_folder.mkdir()

    dst_folder = tmp_path / "dst"
    dst_folder.mkdir()

    src_init = src_folder / "__init__.py"
    src_foo = src_folder / "foo.py"
    src_bar = src_folder / "bar.py"

    src_init.touch()
    src_foo.write_text("a = 5")
    src_bar.write_text("b = 6")

    _download_generic(dst_folder, str(src_folder))

    assert (dst_folder / "__init__.py").exists()
    assert (dst_folder / "foo.py").read_text() == "a = 5"
    assert (dst_folder / "bar.py").read_text() == "b = 6"
