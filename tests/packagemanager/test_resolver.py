"""Tests for dependency resolver."""

import logging

import pytest

from belay.packagemanager.package_json import PackageJson
from belay.packagemanager.resolver import (
    CircularDependencyError,
    ResolvedFile,
    ResolvedPackage,
    resolve_dependencies,
)


@pytest.fixture
def mock_fetch(mocker):
    """Fixture that returns a configurable mock for fetch_package_json."""
    return mocker.patch("belay.packagemanager.resolver.fetch_package_json")


def test_resolve_simple_package(mock_fetch):
    """Test resolving a package with no dependencies."""
    mock_fetch.return_value = PackageJson(
        urls=[("file.py", "https://example.com/file.py")],
        version="1.0",
        base_url="https://example.com/",
    )

    result = resolve_dependencies("test-pkg")

    assert len(result) == 1
    pkg = result[0]
    assert pkg.name == "test-pkg"
    assert pkg.version == "1.0"
    assert len(pkg.files) == 1
    assert pkg.files[0].dest_path == "file.py"
    assert pkg.files[0].hash is None  # URL-based = no hash


def test_resolve_with_hashes(mock_fetch):
    """Test resolving a package with hash-based files (index packages)."""
    mock_fetch.return_value = PackageJson(
        hashes=[("pkg/__init__.mpy", "abcd1234"), ("pkg/utils.mpy", "ef985678")],
        version="1.0",
        base_url="https://micropython.org/pi/v2/",  # base_url set by fetch_package_json
    )

    result = resolve_dependencies("test-pkg", indices=["https://micropython.org/pi/v2"])

    assert len(result) == 1
    pkg = result[0]
    assert len(pkg.files) == 2
    assert pkg.files[0].source_url == "https://micropython.org/pi/v2/file/ab/abcd1234"
    assert pkg.files[0].hash == "abcd1234"
    assert pkg.files[1].hash == "ef985678"


def test_resolve_with_dependencies(mock_fetch):
    """Test resolving a package with dependencies."""

    def side_effect(package, version, indices, mpy_version):
        pkgs = {
            "parent": PackageJson(
                urls=[("parent.py", "https://example.com/parent.py")],
                deps=[("child", "1.0")],
                version="1.0",
                base_url="https://example.com/",
            ),
            "child": PackageJson(
                urls=[("child.py", "https://example.com/child.py")],
                version="1.0",
                base_url="https://example.com/",
            ),
        }
        return pkgs[package]

    mock_fetch.side_effect = side_effect

    result = resolve_dependencies("parent")

    assert len(result) == 2
    names = {pkg.name for pkg in result}
    assert names == {"parent", "child"}


def test_resolve_diamond_dependency(mock_fetch):
    """Test diamond dependency pattern (A -> B, C; B -> D; C -> D) with deduplication."""
    fetch_calls = []

    def side_effect(package, version, indices, mpy_version):
        fetch_calls.append(package)
        pkgs = {
            "A": PackageJson(deps=[("B", "1.0"), ("C", "1.0")], version="1.0"),
            "B": PackageJson(deps=[("D", "1.0")], version="1.0"),
            "C": PackageJson(deps=[("D", "1.0")], version="1.0"),
            "D": PackageJson(
                urls=[("d.py", "https://example.com/d.py")], version="1.0", base_url="https://example.com/"
            ),
        }
        return pkgs[package]

    mock_fetch.side_effect = side_effect

    result = resolve_dependencies("A")

    assert len(result) == 4
    assert fetch_calls.count("D") == 1  # D fetched only once


@pytest.mark.parametrize(
    "deps_a,deps_b",
    [
        ([("pkg-b", "latest")], [("pkg-a", "latest")]),  # A -> B -> A
        ([("pkg-b", "1.0")], [("pkg-a", "2.0")]),  # Different versions still detected
        ([("pkg-a", "latest")], []),  # Self-referential
    ],
)
def test_resolve_circular_dependency(mock_fetch, deps_a, deps_b):
    """Test that circular dependencies raise an error."""
    call_count = {"value": 0}

    def side_effect(package, version, indices, mpy_version):
        call_count["value"] += 1
        if call_count["value"] > 10:
            pytest.fail("Too many calls - infinite loop detected")
        if package == "pkg-a":
            return PackageJson(deps=deps_a, version="1.0")
        elif package == "pkg-b":
            return PackageJson(deps=deps_b, version="1.0")
        raise ValueError(f"Unknown package: {package}")

    mock_fetch.side_effect = side_effect

    with pytest.raises(CircularDependencyError):
        resolve_dependencies("pkg-a")


def test_resolve_version_conflict_warning(mock_fetch, caplog):
    """Test that version conflicts generate a warning but use first-wins."""

    def side_effect(package, version, indices, mpy_version):
        if package == "parent":
            return PackageJson(deps=[("child", "1.0"), ("child", "2.0")], version="1.0")
        elif package == "child":
            return PackageJson(
                urls=[("child.py", "https://example.com/child.py")],
                version=version,
                base_url="https://example.com/",
            )
        raise ValueError(f"Unknown package: {package}")

    mock_fetch.side_effect = side_effect

    with caplog.at_level(logging.WARNING):
        result = resolve_dependencies("parent")

    assert any("Version conflict" in record.message for record in caplog.records)
    # First-wins: child@1.0 should be resolved, not child@2.0
    child_pkg = next(pkg for pkg in result if pkg.name == "child")
    assert child_pkg.version == "1.0"


def test_resolve_github_url(mock_fetch):
    """Test resolving a package from GitHub URL."""
    mock_fetch.return_value = PackageJson(
        urls=[("lib.py", "github:user/repo/lib.py@main")],
        version="0.1",
    )

    result = resolve_dependencies("github:user/mylib")

    assert len(result) == 1
    pkg = result[0]
    assert pkg.files[0].source_url == "https://raw.githubusercontent.com/user/repo/main/lib.py"


def test_resolved_file_dataclass():
    """Test ResolvedFile dataclass attributes."""
    rf = ResolvedFile(
        dest_path="pkg/module.py",
        source_url="https://example.com/module.py",
        hash="abcd1234",
    )
    assert rf.dest_path == "pkg/module.py"
    assert rf.source_url == "https://example.com/module.py"
    assert rf.hash == "abcd1234"

    # Default hash is None
    rf2 = ResolvedFile("a.py", "https://example.com/a.py")
    assert rf2.hash is None


def test_resolved_package_dataclass():
    """Test ResolvedPackage dataclass attributes."""
    rp = ResolvedPackage(
        name="my-pkg",
        version="1.0.0",
        files=[ResolvedFile("a.py", "https://example.com/a.py")],
    )
    assert rp.name == "my-pkg"
    assert rp.version == "1.0.0"
    assert len(rp.files) == 1
