import pytest
import tomlkit

from belay.cli.add import (
    _add_dependency_to_toml,
    _check_dependency_not_exists,
    add,
    infer_package_name,
)
from belay.cli.main import app
from belay.helpers import sanitize_package_name
from belay.packagemanager.downloaders.git import split_version_suffix
from tests.conftest import run_cli

# Tests for _add_dependency_to_toml


def test_add_dependency_to_toml_simple(tmp_cwd):
    pyproject = tmp_cwd / "pyproject.toml"
    pyproject.write_text("[tool.belay]\nname = 'myproject'\n")

    _add_dependency_to_toml(
        pyproject_path=pyproject,
        package="foo",
        uri="https://github.com/user/foo",
        group="main",
        develop=False,
        rename_to_init=True,
    )

    doc = tomlkit.parse(pyproject.read_text())
    assert doc["tool"]["belay"]["dependencies"]["foo"] == "https://github.com/user/foo"


def test_add_dependency_to_toml_develop(tmp_cwd):
    pyproject = tmp_cwd / "pyproject.toml"
    pyproject.write_text("[tool.belay]\nname = 'myproject'\n")

    _add_dependency_to_toml(
        pyproject_path=pyproject,
        package="mylib",
        uri="/path/to/local",
        group="main",
        develop=True,
        rename_to_init=True,
    )

    doc = tomlkit.parse(pyproject.read_text())
    dep = doc["tool"]["belay"]["dependencies"]["mylib"]
    assert dep["uri"] == "/path/to/local"
    assert dep["develop"] is True


def test_add_dependency_to_toml_no_rename_to_init(tmp_cwd):
    pyproject = tmp_cwd / "pyproject.toml"
    pyproject.write_text("[tool.belay]\nname = 'myproject'\n")

    _add_dependency_to_toml(
        pyproject_path=pyproject,
        package="multi_file",
        uri="https://github.com/user/multi_file",
        group="main",
        develop=False,
        rename_to_init=False,
    )

    doc = tomlkit.parse(pyproject.read_text())
    dep = doc["tool"]["belay"]["dependencies"]["multi_file"]
    assert dep["uri"] == "https://github.com/user/multi_file"
    assert dep["rename_to_init"] is False


def test_add_dependency_to_toml_named_group(tmp_cwd):
    pyproject = tmp_cwd / "pyproject.toml"
    pyproject.write_text("[tool.belay]\nname = 'myproject'\n")

    _add_dependency_to_toml(
        pyproject_path=pyproject,
        package="test_helper",
        uri="https://github.com/user/test_helper",
        group="dev",
        develop=False,
        rename_to_init=True,
    )

    doc = tomlkit.parse(pyproject.read_text())
    assert doc["tool"]["belay"]["group"]["dev"]["dependencies"]["test_helper"] == "https://github.com/user/test_helper"


def test_add_dependency_to_toml_creates_belay_section(tmp_cwd):
    pyproject = tmp_cwd / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'myproject'\n")

    _add_dependency_to_toml(
        pyproject_path=pyproject,
        package="foo",
        uri="https://example.com/foo",
        group="main",
        develop=False,
        rename_to_init=True,
    )

    doc = tomlkit.parse(pyproject.read_text())
    assert doc["tool"]["belay"]["dependencies"]["foo"] == "https://example.com/foo"
    assert doc["project"]["name"] == "myproject"  # Preserved


def test_check_dependency_not_exists_raises(tmp_cwd):
    pyproject = tmp_cwd / "pyproject.toml"
    pyproject.write_text("[tool.belay.dependencies]\nfoo = 'https://example.com/foo'\n")

    with pytest.raises(ValueError, match="already exists"):
        _check_dependency_not_exists(pyproject, "foo", "main")


def test_check_dependency_not_exists_passes(tmp_cwd):
    pyproject = tmp_cwd / "pyproject.toml"
    pyproject.write_text("[tool.belay.dependencies]\nfoo = 'https://example.com/foo'\n")

    # Should not raise for a different package
    _check_dependency_not_exists(pyproject, "bar", "main")


# Tests for add function


def test_add_invalid_package_name(tmp_cwd):
    pyproject = tmp_cwd / "pyproject.toml"
    pyproject.write_text("[tool.belay]\n")

    with pytest.raises(ValueError, match="valid Python identifier"):
        add("invalid-name", "https://example.com/pkg")


def test_add_downloads_then_writes(mocker, tmp_cwd):
    """Test that add() downloads first, then writes to pyproject.toml."""
    pyproject = tmp_cwd / "pyproject.toml"
    pyproject.write_text("[tool.belay]\n")
    mock_download = mocker.patch("belay.packagemanager.group.Group._download_package")

    add("foo", "https://example.com/foo")

    mock_download.assert_called_once_with("foo")
    doc = tomlkit.parse(pyproject.read_text())
    assert doc["tool"]["belay"]["dependencies"]["foo"] == "https://example.com/foo"


def test_add_does_not_write_on_failure(mocker, tmp_cwd):
    """Test that pyproject.toml is not modified if download fails."""
    pyproject = tmp_cwd / "pyproject.toml"
    pyproject.write_text("[tool.belay]\n")

    # Make download raise an exception
    mocker.patch("belay.packagemanager.group.Group._download_package", side_effect=Exception("Download failed"))

    with pytest.raises(Exception, match="Download failed"):
        add("foo", "https://example.com/foo")

    # Verify pyproject.toml was not modified
    doc = tomlkit.parse(pyproject.read_text())
    assert "dependencies" not in doc.get("tool", {}).get("belay", {})


def test_add_index_package_with_version_stores_correct_uri(mocker, tmp_cwd):
    """Test that 'belay add foobar@v1.0.0' stores a downloadable URI, not just the version.

    Regression test: Previously, 'belay add foobar@v1.0.0' would store
    'foobar = "v1.0.0"' in pyproject.toml. When update() ran, it would try
    to download "v1.0.0" as a local file path, causing FileNotFoundError.
    """
    pyproject = tmp_cwd / "pyproject.toml"
    pyproject.write_text("[tool.belay]\n")
    mocker.patch("belay.packagemanager.group.Group._download_package")

    add("foobar@v1.0.0")

    doc = tomlkit.parse(pyproject.read_text())
    stored_value = doc["tool"]["belay"]["dependencies"]["foobar"]
    # The stored URI should be something the download system can handle,
    # NOT just "v1.0.0" which would be interpreted as a local file path
    assert stored_value != "v1.0.0", "Version alone is not a valid downloadable URI"
    # Should store the full package reference that can be looked up in the index
    assert "foobar" in stored_value


def test_add_single_arg_infers_name(mocker, tmp_cwd):
    pyproject = tmp_cwd / "pyproject.toml"
    pyproject.write_text("[tool.belay]\n")
    mocker.patch("belay.packagemanager.group.Group._download_package")

    add("https://github.com/user/repo/tree/main/sensor")

    doc = tomlkit.parse(pyproject.read_text())
    assert doc["tool"]["belay"]["dependencies"]["sensor"] == "https://github.com/user/repo/tree/main/sensor"


# Tests for CLI


def test_cli_add(mocker, tmp_cwd):
    pyproject = tmp_cwd / "pyproject.toml"
    pyproject.write_text("[tool.belay]\n")
    mocker.patch("belay.packagemanager.group.Group._download_package")

    assert run_cli(app, ["add", "mypkg", "https://example.com/mypkg"]) == 0
    assert "mypkg" in pyproject.read_text()


def test_cli_add_single_arg(mocker, tmp_cwd):
    pyproject = tmp_cwd / "pyproject.toml"
    pyproject.write_text("[tool.belay]\n")
    mocker.patch("belay.packagemanager.group.Group._download_package")

    assert run_cli(app, ["add", "https://github.com/user/repo/tree/main/bme280"]) == 0
    doc = tomlkit.parse(pyproject.read_text())
    assert "bme280" in doc["tool"]["belay"]["dependencies"]


# Tests for sanitize_package_name


@pytest.mark.parametrize(
    "input_name,expected",
    [
        ("module.py", "module"),
        ("module.mpy", "module"),
        ("my-package", "my_package"),
        ("my-module.py", "my_module"),
    ],
)
def test_sanitize_package_name(input_name, expected):
    assert sanitize_package_name(input_name) == expected


def test_sanitize_package_name_invalid():
    with pytest.raises(ValueError, match="Cannot convert"):
        sanitize_package_name("123invalid")


# Tests for infer_package_name


@pytest.mark.parametrize(
    "uri,expected",
    [
        ("https://github.com/user/repo/tree/main/bme280", "bme280"),
        ("https://github.com/user/repo/blob/main/sensor.py", "sensor"),
        ("https://github.com/user/micropython-dht", "micropython_dht"),
        ("https://github.com/user/my-lib.git", "my_lib"),
        ("https://raw.githubusercontent.com/user/repo/main/lib.py", "lib"),
        ("/home/user/projects/mylib", "mylib"),
        ("./local/module", "module"),
    ],
)
def test_infer_package_name(uri, expected):
    assert infer_package_name(uri) == expected


def test_infer_package_name_unknown_uri():
    with pytest.raises(ValueError, match="Cannot infer package name"):
        infer_package_name("ftp://example.com/something")


# Tests for split_version_suffix


@pytest.mark.parametrize(
    "uri,expected_base,expected_version",
    [
        ("aiohttp", "aiohttp", None),
        ("aiohttp@1.0.0", "aiohttp", "1.0.0"),
        ("aiohttp==1.0.0", "aiohttp", "1.0.0"),
        ("mip:aiohttp", "mip:aiohttp", None),
        ("mip:aiohttp@2.0", "mip:aiohttp", "2.0"),
        ("mip:aiohttp==2.0", "mip:aiohttp", "2.0"),
        ("github:user/repo@v1.0", "github:user/repo", "v1.0"),
        ("https://example.com/file.py", "https://example.com/file.py", None),
        ("https://user@example.com/file.py", "https://user@example.com/file.py", None),
    ],
)
def test_split_version_suffix(uri, expected_base, expected_version):
    base, version = split_version_suffix(uri)
    assert base == expected_base
    assert version == expected_version


# Tests for infer_package_name with index packages


@pytest.mark.parametrize(
    "uri,expected",
    [
        # Plain package names
        ("aiohttp", "aiohttp"),
        ("micropython_lib", "micropython_lib"),
        ("my-package", "my_package"),
        # Versioned packages (@ syntax)
        ("aiohttp@1.0.0", "aiohttp"),
        ("my-lib@2.0", "my_lib"),
        # Versioned packages (== syntax)
        ("aiohttp==1.0.0", "aiohttp"),
        ("my-lib==2.0", "my_lib"),
        # mip: prefix
        ("mip:aiohttp", "aiohttp"),
        ("mip:my-package", "my_package"),
        ("mip:aiohttp@1.0.0", "aiohttp"),
        ("mip:aiohttp==1.0.0", "aiohttp"),
        # github:/gitlab: shorthand
        ("github:user/repo", "repo"),
        ("github:user/my-repo", "my_repo"),
        ("github:user/repo@v1.0", "repo"),
        ("github:user/repo/path/module", "module"),
        ("github:user/repo/path/module.py", "module"),
        ("gitlab:user/repo", "repo"),
        ("gitlab:user/repo/lib.py@main", "lib"),
    ],
)
def test_infer_package_name_index_and_shorthand(uri, expected):
    assert infer_package_name(uri) == expected


# Tests for add with index packages and shorthand


@pytest.mark.parametrize(
    "uri,expected_pkg,expected_value",
    [
        # Index packages - store full package reference so download system can recognize them
        ("aiohttp", "aiohttp", "aiohttp"),
        ("aiohttp@1.0.0", "aiohttp", "aiohttp@1.0.0"),
        ("aiohttp==1.0.0", "aiohttp", "aiohttp==1.0.0"),
        ("mip:requests", "requests", "mip:requests"),
        ("mip:requests@2.0", "requests", "mip:requests@2.0"),
        ("mip:requests==2.0", "requests", "mip:requests==2.0"),
        # github:/gitlab: shorthand (NOT index packages, URI preserved)
        ("github:user/repo@v1.0", "repo", "github:user/repo@v1.0"),
        (
            "github:micropython/micropython-lib/python-stdlib/pathlib",
            "pathlib",
            "github:micropython/micropython-lib/python-stdlib/pathlib",
        ),
    ],
)
def test_add_index_and_shorthand(mocker, tmp_cwd, uri, expected_pkg, expected_value):
    pyproject = tmp_cwd / "pyproject.toml"
    pyproject.write_text("[tool.belay]\n")
    mocker.patch("belay.packagemanager.group.Group._download_package")

    add(uri)

    doc = tomlkit.parse(pyproject.read_text())
    assert doc["tool"]["belay"]["dependencies"][expected_pkg] == expected_value


# Tests for CLI with index packages


@pytest.mark.parametrize(
    "uri,expected_pkg,expected_value",
    [
        ("aiohttp", "aiohttp", "aiohttp"),
        ("aiohttp@1.0.0", "aiohttp", "aiohttp@1.0.0"),
        ("github:user/mylib", "mylib", "github:user/mylib"),
    ],
)
def test_cli_add_index_and_shorthand(mocker, tmp_cwd, uri, expected_pkg, expected_value):
    pyproject = tmp_cwd / "pyproject.toml"
    pyproject.write_text("[tool.belay]\n")
    mocker.patch("belay.packagemanager.group.Group._download_package")

    assert run_cli(app, ["add", uri]) == 0
    doc = tomlkit.parse(pyproject.read_text())
    assert doc["tool"]["belay"]["dependencies"][expected_pkg] == expected_value
