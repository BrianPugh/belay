import pytest
from pydantic import ValidationError

from belay.packagemanager import BelayConfig, GroupConfig
from belay.packagemanager.models import (
    VersionRangeNotSupportedError,
    _transform_version_uri,
)


def test_group_config_multiple_rename_to_init():
    dependencies = {
        "package": [
            {"uri": "foo", "rename_to_init": True},
            {"uri": "bar", "rename_to_init": True},
        ]
    }
    with pytest.raises(ValidationError):
        GroupConfig(dependencies=dependencies)


def test_belay_config_valid_package_indices():
    """Test that valid package index URLs are accepted."""
    config = BelayConfig(package_indices=["https://micropython.org/pi/v2", "http://example.com/index"])
    assert config.package_indices == ["https://micropython.org/pi/v2", "http://example.com/index"]


@pytest.mark.parametrize(
    "invalid_url,error_fragment",
    [
        ("ftp://example.com/index", "must be http:// or https://"),
        ("file:///local/path", "must be http:// or https://"),
        ("not-a-url", "must be http:// or https://"),
        ("https://", "missing host"),
    ],
)
def test_belay_config_invalid_package_indices(invalid_url, error_fragment):
    """Test that invalid package index URLs raise validation errors."""
    with pytest.raises(ValidationError) as exc_info:
        BelayConfig(package_indices=[invalid_url])
    assert error_fragment in str(exc_info.value)


@pytest.mark.parametrize(
    "mpy_version",
    [
        "py",  # Pure Python source
        "6",  # Compiled .mpy version 6
        "5",  # Compiled .mpy version 5
        "123",  # Any numeric string
    ],
)
def test_belay_config_valid_mpy_version(mpy_version):
    """Test that valid mpy_version values are accepted."""
    config = BelayConfig(mpy_version=mpy_version)
    assert config.mpy_version == mpy_version


@pytest.mark.parametrize(
    "invalid_mpy_version,error_fragment",
    [
        ("", "cannot be empty"),
        ("python", 'Use "py" for pure Python'),
        ("abc", 'Use "py" for pure Python'),
        ("6.0", 'Use "py" for pure Python'),  # Not purely numeric
        ("py6", 'Use "py" for pure Python'),  # Not "py" or numeric
    ],
)
def test_belay_config_invalid_mpy_version(invalid_mpy_version, error_fragment):
    """Test that invalid mpy_version values raise validation errors."""
    with pytest.raises(ValidationError) as exc_info:
        BelayConfig(mpy_version=invalid_mpy_version)
    assert error_fragment in str(exc_info.value)


# Tests for version/wildcard URI transformation


@pytest.mark.parametrize(
    "package_name,uri,expected",
    [
        # Wildcard -> package name
        ("aiohttp", "*", "aiohttp"),
        ("requests", "latest", "requests"),
        # Version -> package@version
        ("aiohttp", "1.0.0", "aiohttp@1.0.0"),
        ("requests", "2.1", "requests@2.1"),
        ("mylib", "0.5.1.2", "mylib@0.5.1.2"),
        # Pass-through cases (URLs, paths, explicit mip:, etc.)
        ("pathlib", "github:user/repo", "github:user/repo"),
        ("mylib", "gitlab:org/project@main", "gitlab:org/project@main"),
        ("foo", "https://example.com/foo.py", "https://example.com/foo.py"),
        ("bar", "../local/path.py", "../local/path.py"),
        ("baz", "mip:somepackage", "mip:somepackage"),
        ("qux", "aiohttp", "aiohttp"),  # explicit package name
        # Empty string passes through
        ("pkg", "", ""),
    ],
)
def test_transform_version_uri(package_name, uri, expected):
    """Test _transform_version_uri transforms version syntax correctly."""
    assert _transform_version_uri(package_name, uri) == expected


@pytest.mark.parametrize(
    "uri",
    [
        "^1.0.0",
        "~1.0.0",
        ">=1.0.0",
        "<=2.0",
        ">1.0",
        "<2.0",
        "!=1.5.0",
        "=1.0.0",
    ],
)
def test_transform_version_uri_range_not_supported(uri):
    """Test that version ranges raise VersionRangeNotSupportedError."""
    with pytest.raises(VersionRangeNotSupportedError) as exc_info:
        _transform_version_uri("mypackage", uri)
    assert "Version ranges are not supported" in str(exc_info.value)
    assert '"*" for latest' in str(exc_info.value)


def test_group_config_wildcard_dependency():
    """Test GroupConfig parses wildcard dependency syntax."""
    config = GroupConfig(dependencies={"aiohttp": "*"})
    assert len(config.dependencies["aiohttp"]) == 1
    assert config.dependencies["aiohttp"][0].uri == "aiohttp"


def test_group_config_version_dependency():
    """Test GroupConfig parses version dependency syntax."""
    config = GroupConfig(dependencies={"requests": "1.0.0"})
    assert config.dependencies["requests"][0].uri == "requests@1.0.0"


def test_group_config_latest_dependency():
    """Test GroupConfig parses 'latest' dependency syntax."""
    config = GroupConfig(dependencies={"ntptime": "latest"})
    assert config.dependencies["ntptime"][0].uri == "ntptime"


def test_group_config_dict_with_version():
    """Test GroupConfig parses dict with version URI."""
    config = GroupConfig(dependencies={"aiohttp": {"uri": "1.0.0"}})
    assert config.dependencies["aiohttp"][0].uri == "aiohttp@1.0.0"


def test_group_config_dict_with_wildcard():
    """Test GroupConfig parses dict with wildcard URI."""
    config = GroupConfig(dependencies={"aiohttp": {"uri": "*", "develop": True}})
    assert config.dependencies["aiohttp"][0].uri == "aiohttp"
    assert config.dependencies["aiohttp"][0].develop is True


def test_group_config_version_range_error():
    """Test GroupConfig raises error for version ranges."""
    with pytest.raises(ValidationError) as exc_info:
        GroupConfig(dependencies={"aiohttp": "^1.0.0"})
    assert "Version ranges are not supported" in str(exc_info.value)


def test_belay_config_wildcard_dependency():
    """Test BelayConfig parses wildcard dependency syntax."""
    config = BelayConfig(dependencies={"aiohttp": "*", "requests": "1.0.0"})
    assert config.dependencies["aiohttp"][0].uri == "aiohttp"
    assert config.dependencies["requests"][0].uri == "requests@1.0.0"
