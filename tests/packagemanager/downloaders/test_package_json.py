"""Tests for package.json downloader."""

import pytest
import requests

from belay.exceptions import IntegrityError, PackageNotFoundError
from belay.packagemanager.downloaders._package_json import (
    _is_package_json_uri,
    _is_plain_package_name,
    download_package_json,
)
from belay.packagemanager.downloaders.common import NonMatchingURI
from belay.packagemanager.resolver import ResolvedFile, ResolvedPackage


@pytest.mark.parametrize(
    "name,expected",
    [
        # Valid package names
        ("aiohttp", True),
        ("ntptime", True),
        ("micropython-lib", True),
        ("my_package", True),
        ("Package123", True),
        # Invalid - empty
        ("", False),
        # Invalid - contains URL scheme indicators
        ("mip:aiohttp", False),
        ("github:user/repo", False),
        ("https://example.com", False),
        # Invalid - contains path separators
        ("path/to/file", False),
        ("path\\to\\file", False),
        # Invalid - contains file extension
        ("file.py", False),
        ("package.json", False),
        ("lib.mpy", False),
    ],
)
def test_is_plain_package_name(name, expected):
    assert _is_plain_package_name(name) is expected


@pytest.mark.parametrize(
    "uri,expected",
    [
        # Plain package names (index lookup)
        ("aiohttp", True),
        ("ntptime", True),
        ("micropython-lib", True),
        ("my_package", True),
        ("aiohttp@1.0.0", True),
        # mip: prefix (explicit index)
        ("mip:aiohttp", True),
        ("mip:ntptime", True),
        ("mip:aiohttp@1.0.0", True),
        # github:user/repo (package.json at root)
        ("github:user/repo", True),
        ("github:user/repo@main", True),
        ("github:user/repo/lib", True),
        ("github:user/repo/package.json", True),
        # github single files should NOT match
        ("github:user/repo/file.py", False),
        ("github:user/repo/file.mpy", False),
        # gitlab
        ("gitlab:user/repo", True),
        ("gitlab:user/repo@main", True),
        # Explicit .json URLs
        ("https://example.com/package.json", True),
        # Regular URLs should NOT match
        ("https://example.com/file.py", False),
        # Local paths should NOT match (contain / or .)
        ("./local/package.json", True),  # ends with .json
        ("./local/file.py", False),
    ],
)
def test_is_package_json_uri(uri, expected):
    assert _is_package_json_uri(uri) is expected


@pytest.mark.parametrize(
    "uri",
    [
        "https://example.com/file.py",
        "github:user/repo/file.py",
    ],
)
def test_download_package_json_non_matching_raises(tmp_path, uri):
    """Non-matching URIs should raise NonMatchingURI."""
    with pytest.raises(NonMatchingURI):
        download_package_json(tmp_path, uri)


@pytest.fixture
def mock_resolver(mocker):
    """Fixture that mocks the resolve_dependencies function."""
    return mocker.patch("belay.packagemanager.downloaders._package_json.resolve_dependencies")


@pytest.fixture
def mock_requests_get(mocker):
    """Fixture that mocks requests.get in the _retry module."""
    mock = mocker.patch("belay.packagemanager.downloaders._retry.requests.get")
    # Set default status_code to 200 for successful responses
    mock.return_value.status_code = 200
    return mock


def _make_resolved(files):
    """Helper to create a resolved package list."""
    return [
        ResolvedPackage(
            name="test-pkg",
            version="1.0",
            files=[ResolvedFile(dest_path=f[0], source_url=f[1], hash=f[2] if len(f) > 2 else None) for f in files],
        )
    ]


def test_download_package_json_basic(tmp_path, mock_resolver, mock_requests_get):
    """Test basic download with mocked resolver."""
    mock_resolver.return_value = _make_resolved([("test_pkg/__init__.py", "https://example.com/init.py")])
    mock_requests_get.return_value.content = b"# test content"

    result = download_package_json(tmp_path, "mip:test-pkg")

    assert result == tmp_path
    assert (tmp_path / "test_pkg" / "__init__.py").read_bytes() == b"# test content"


def test_download_package_json_plain_name(tmp_path, mock_resolver, mock_requests_get):
    """Test download using plain package name (without mip: prefix)."""
    mock_resolver.return_value = _make_resolved([("aiohttp/__init__.py", "https://example.com/init.py")])
    mock_requests_get.return_value.content = b"# aiohttp content"

    result = download_package_json(tmp_path, "aiohttp")

    assert result == tmp_path
    assert (tmp_path / "aiohttp" / "__init__.py").read_bytes() == b"# aiohttp content"
    # Verify resolve_dependencies was called with the plain name
    assert mock_resolver.call_args[0] == ("aiohttp", "latest")


def test_download_package_json_plain_name_with_version(tmp_path, mock_resolver, mock_requests_get):
    """Test download using plain package name with version."""
    mock_resolver.return_value = _make_resolved([("aiohttp/__init__.py", "https://example.com/init.py")])
    mock_requests_get.return_value.content = b"# aiohttp content"

    result = download_package_json(tmp_path, "aiohttp@1.0.0")

    assert result == tmp_path
    # Verify resolve_dependencies was called with correct version
    assert mock_resolver.call_args[0] == ("aiohttp", "1.0.0")


def test_download_package_json_with_version(tmp_path, mock_resolver, mock_requests_get):
    """Test download with version specified."""
    mock_resolver.return_value = [ResolvedPackage(name="test-pkg", version="1.0.0", files=[])]

    download_package_json(tmp_path, "mip:test-pkg@1.0.0")

    # Verify resolve_dependencies was called with correct package and version
    assert mock_resolver.call_args[0] == ("test-pkg", "1.0.0")


def test_download_package_json_package_not_found(tmp_path, mock_resolver):
    """Test that PackageNotFoundError bubbles up."""
    mock_resolver.side_effect = PackageNotFoundError("Not found")

    with pytest.raises(PackageNotFoundError, match="Not found"):
        download_package_json(tmp_path, "mip:nonexistent-pkg")


def test_download_package_json_hash_verification(tmp_path, mock_resolver, mock_requests_get):
    """Test that hash verification works correctly."""
    content = b"# verified content"
    expected_hash = "5d66c65d"  # sha256(content)[:8]

    mock_resolver.return_value = _make_resolved([("test.py", "https://example.com/test.py", expected_hash)])
    mock_requests_get.return_value.content = content

    download_package_json(tmp_path, "mip:test-pkg")
    assert (tmp_path / "test.py").read_bytes() == content


def test_download_package_json_hash_verification_case_insensitive(tmp_path, mock_resolver, mock_requests_get):
    """Test that hash verification is case-insensitive."""
    content = b"# verified content"
    expected_hash = "5D66C65D"  # sha256(content)[:8] uppercased

    mock_resolver.return_value = _make_resolved([("test.py", "https://example.com/test.py", expected_hash)])
    mock_requests_get.return_value.content = content

    # Should succeed even though computed hash is lowercase and expected is uppercase
    download_package_json(tmp_path, "mip:test-pkg")
    assert (tmp_path / "test.py").read_bytes() == content


def test_download_package_json_hash_mismatch(tmp_path, mock_resolver, mock_requests_get):
    """Test that hash mismatch raises IntegrityError."""
    mock_resolver.return_value = _make_resolved([("test.py", "https://example.com/test.py", "deadbeef")])
    mock_requests_get.return_value.content = b"# different content"

    with pytest.raises(IntegrityError, match="Hash mismatch"):
        download_package_json(tmp_path, "mip:test-pkg")


def test_download_package_json_retry_on_timeout(tmp_path, mock_resolver, mock_requests_get, mocker):
    """Test that download retries on timeout and succeeds."""
    mocker.patch("tenacity.nap.time.sleep")  # Disable tenacity's sleep for fast tests
    mock_resolver.return_value = _make_resolved([("test.py", "https://example.com/test.py")])

    success_response = mocker.MagicMock()
    success_response.status_code = 200
    success_response.content = b"# success"

    mock_requests_get.side_effect = [
        requests.exceptions.Timeout("timeout 1"),
        requests.exceptions.Timeout("timeout 2"),
        success_response,
    ]

    result = download_package_json(tmp_path, "mip:test-pkg")
    assert result == tmp_path
    assert mock_requests_get.call_count == 3


def test_download_package_json_retry_exhausted(tmp_path, mock_resolver, mock_requests_get, mocker):
    """Test that download fails after retries exhausted."""
    mocker.patch("tenacity.nap.time.sleep")  # Disable tenacity's sleep for fast tests
    mock_resolver.return_value = _make_resolved([("test.py", "https://example.com/test.py")])
    mock_requests_get.side_effect = requests.exceptions.Timeout("always timeout")

    with pytest.raises(PackageNotFoundError, match="Failed to download"):
        download_package_json(tmp_path, "mip:test-pkg")


def test_download_package_json_retry_on_rate_limit(tmp_path, mock_resolver, mock_requests_get, mocker):
    """Test that download retries on 429 rate limit."""
    mocker.patch("tenacity.nap.time.sleep")  # Disable tenacity's sleep for fast tests
    mock_resolver.return_value = _make_resolved([("test.py", "https://example.com/test.py")])

    rate_limit_response = mocker.MagicMock()
    rate_limit_response.status_code = 429
    rate_limit_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=rate_limit_response)

    success_response = mocker.MagicMock()
    success_response.status_code = 200
    success_response.content = b"# success"
    success_response.raise_for_status.return_value = None  # Explicitly set to not raise

    mock_requests_get.side_effect = [rate_limit_response, success_response]

    result = download_package_json(tmp_path, "mip:test-pkg")
    assert result == tmp_path
    assert mock_requests_get.call_count == 2


def test_download_package_json_no_retry_on_404(tmp_path, mock_resolver, mock_requests_get, mocker):
    """Test that 404 errors are not retried."""
    mock_resolver.return_value = _make_resolved([("test.py", "https://example.com/test.py")])

    not_found_response = mocker.MagicMock()
    not_found_response.status_code = 404
    not_found_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=not_found_response)
    mock_requests_get.return_value = not_found_response

    with pytest.raises(PackageNotFoundError, match="Failed to download"):
        download_package_json(tmp_path, "mip:test-pkg")

    assert mock_requests_get.call_count == 1


@pytest.mark.network
def test_download_package_json_real_package(tmp_path):
    """Test downloading a real package from the index using mip: prefix."""
    result = download_package_json(tmp_path, "mip:ntptime")

    assert result == tmp_path
    files = list(tmp_path.rglob("*"))
    assert len([f for f in files if f.is_file()]) > 0


@pytest.mark.network
def test_download_package_json_real_package_plain_name(tmp_path):
    """Test downloading a real package using plain package name."""
    result = download_package_json(tmp_path, "ntptime")

    assert result == tmp_path
    files = list(tmp_path.rglob("*"))
    assert len([f for f in files if f.is_file()]) > 0
