"""Tests for MicroPython package.json support."""

import pytest

from belay.exceptions import PackageNotFoundError
from belay.packagemanager.downloaders import rewrite_url
from belay.packagemanager.package_json import (
    PackageJson,
    is_index_hash,
)
from belay.packagemanager.resolver import resolve_file_url


@pytest.mark.parametrize(
    "value,expected",
    [
        # Valid hashes (case-insensitive)
        ("abcd1234", True),
        ("00000000", True),
        ("ffffffff", True),
        ("12345678", True),
        ("ABCD1234", True),  # Uppercase is valid
        ("AbCd1234", True),  # Mixed case is valid
        ("FFFFFFFF", True),
        # Invalid length
        ("abcd123", False),
        ("abcd12345", False),
        ("", False),
        ("abcd", False),
        # Invalid chars
        ("abcdxyz1", False),
        ("abcd123g", False),
        ("file.py!", False),
    ],
)
def test_is_index_hash(value, expected):
    assert is_index_hash(value) is expected


@pytest.mark.parametrize(
    "url,branch,expected",
    [
        # GitHub basic
        ("github:user/repo/path/file.py", "HEAD", "https://raw.githubusercontent.com/user/repo/HEAD/path/file.py"),
        ("github:user/repo/path/file.py@main", "HEAD", "https://raw.githubusercontent.com/user/repo/main/path/file.py"),
        (
            "github:user/repo/path/file.py@v1.2.3",
            "HEAD",
            "https://raw.githubusercontent.com/user/repo/v1.2.3/path/file.py",
        ),
        ("github:user/repo@main", "HEAD", "https://raw.githubusercontent.com/user/repo/main"),
        ("github:user/repo", "HEAD", "https://raw.githubusercontent.com/user/repo/HEAD"),
        ("github:user/repo/file.py", "develop", "https://raw.githubusercontent.com/user/repo/develop/file.py"),
        # GitLab
        ("gitlab:user/repo/path/file.py", "HEAD", "https://gitlab.com/user/repo/-/raw/HEAD/path/file.py"),
        ("gitlab:user/repo/path/file.py@develop", "HEAD", "https://gitlab.com/user/repo/-/raw/develop/path/file.py"),
        # Passthrough
        ("https://example.com/file.py", "HEAD", "https://example.com/file.py"),
        ("http://example.com/file.py", "HEAD", "http://example.com/file.py"),
    ],
)
def test_rewrite_url(url, branch, expected):
    assert rewrite_url(url, branch=branch) == expected


@pytest.mark.parametrize("url", ["github:invalid", "gitlab:onlyuser"])
def test_rewrite_url_invalid(url):
    with pytest.raises(ValueError, match="Invalid (github|gitlab) URL"):
        rewrite_url(url)


def test_package_json_from_dict():
    # Full data
    data = {
        "urls": [["dest.py", "source.py"]],
        "hashes": [["file.mpy", "abcd1234"]],
        "deps": [["pkg", "1.0"]],
        "version": "0.1.0",
    }
    pkg = PackageJson.from_dict(data, base_url="https://example.com/")
    assert pkg.urls == [("dest.py", "source.py")]
    assert pkg.hashes == [("file.mpy", "abcd1234")]
    assert pkg.deps == [("pkg", "1.0")]
    assert pkg.version == "0.1.0"
    assert pkg.base_url == "https://example.com/"

    # Empty data
    pkg = PackageJson.from_dict({})
    assert pkg.urls == []
    assert pkg.deps == []
    assert pkg.hashes == []
    assert pkg.version == ""


@pytest.mark.parametrize(
    "data,match",
    [
        ({"urls": ["not-a-tuple"]}, "Invalid urls entry"),
        ({"urls": [["only-one-element"]]}, "Invalid urls entry"),
        ({"hashes": ["not-a-tuple"]}, "Invalid hashes entry"),
        ({"deps": ["not-a-tuple"]}, "Invalid deps entry"),
        ({"version": 123}, "Invalid version"),
    ],
)
def test_package_json_from_dict_invalid(data, match):
    with pytest.raises(ValueError, match=match):
        PackageJson.from_dict(data)


@pytest.mark.parametrize(
    "base_url,source,expected",
    [
        # Absolute URL
        ("https://base.com/pkg/", "https://other.com/file.py", "https://other.com/file.py"),
        # Relative URLs
        ("https://example.com/repo/", "lib/file.py", "https://example.com/repo/lib/file.py"),
        ("https://example.com/repo/subdir/", "../file.py", "https://example.com/repo/file.py"),
        # Shorthand
        ("", "github:user/repo/file.py@main", "https://raw.githubusercontent.com/user/repo/main/file.py"),
        ("", "gitlab:user/repo/file.py@develop", "https://gitlab.com/user/repo/-/raw/develop/file.py"),
        # Hash-based (index packages) - base_url contains the index
        ("https://micropython.org/pi/v2/", "abcd1234", "https://micropython.org/pi/v2/file/ab/abcd1234"),
        ("https://micropython.org/pi/v2/", "12345678", "https://micropython.org/pi/v2/file/12/12345678"),
        # Not a hash (wrong length or chars) - resolved as relative URL
        ("https://example.com/", "abcd123", "https://example.com/abcd123"),
        ("https://example.com/", "abcdxyz1", "https://example.com/abcdxyz1"),
    ],
)
def test_resolve_file_url(base_url, source, expected):
    pkg = PackageJson(base_url=base_url)
    url = resolve_file_url(pkg, "file.py", source)
    assert url == expected


@pytest.mark.network
def test_fetch_package_json_from_index():
    """Test fetching a real package from micropython.org index."""
    from belay.packagemanager.package_json import fetch_package_json

    pkg = fetch_package_json("ntptime", mpy_version="py")
    assert pkg.version
    assert len(pkg.hashes) > 0 or len(pkg.urls) > 0


@pytest.mark.network
def test_fetch_package_json_not_found():
    """Test that nonexistent packages raise PackageNotFoundError."""
    from belay.packagemanager.package_json import fetch_package_json

    with pytest.raises(PackageNotFoundError):
        fetch_package_json("this-package-definitely-does-not-exist-12345")


def test_fetch_package_json_multiple_indices_fallback(mocker):
    """Test that multiple indices are tried in order."""
    from belay.packagemanager.package_json import fetch_package_json

    mock_get = mocker.patch("belay.packagemanager.package_json.requests.get")

    # First index returns 404, second succeeds
    first_response = mocker.MagicMock()
    first_response.status_code = 404

    second_response = mocker.MagicMock()
    second_response.status_code = 200
    second_response.json.return_value = {"urls": [["file.py", "https://example.com/file.py"]], "version": "1.0"}

    mock_get.side_effect = [first_response, second_response]

    pkg = fetch_package_json("test-pkg", indices=["https://first.com", "https://second.com"])

    assert pkg.version == "1.0"
    assert pkg.base_url == "https://second.com/"
    assert mock_get.call_count == 2


def test_fetch_package_json_multiple_indices_first_succeeds(mocker):
    """Test that first index is used when it succeeds."""
    from belay.packagemanager.package_json import fetch_package_json

    mock_get = mocker.patch("belay.packagemanager.package_json.requests.get")

    response = mocker.MagicMock()
    response.status_code = 200
    response.json.return_value = {"urls": [["file.py", "https://example.com/file.py"]], "version": "1.0"}
    mock_get.return_value = response

    pkg = fetch_package_json("test-pkg", indices=["https://first.com", "https://second.com"])

    assert pkg.base_url == "https://first.com/"
    assert mock_get.call_count == 1


def test_fetch_package_json_multiple_indices_all_fail(mocker):
    """Test that PackageNotFoundError is raised when all indices fail."""
    from belay.packagemanager.package_json import fetch_package_json

    mock_get = mocker.patch("belay.packagemanager.package_json.requests.get")

    response = mocker.MagicMock()
    response.status_code = 404
    mock_get.return_value = response

    with pytest.raises(PackageNotFoundError, match="not found in any index"):
        fetch_package_json("test-pkg", indices=["https://first.com", "https://second.com"])

    assert mock_get.call_count == 2
