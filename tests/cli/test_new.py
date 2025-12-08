from textwrap import dedent

import pytest

from belay.cli.new import new


def test_new_creates_project_in_new_directory(tmp_cwd):
    """Test that belay new creates a project in a new directory."""
    project_name = "my-project"

    new(project_name)

    project_dir = tmp_cwd / project_name
    assert project_dir.exists()
    assert (project_dir / "pyproject.toml").exists()
    assert (project_dir / "main.py").exists()
    assert (project_dir / "my-project" / "__init__.py").exists()

    # Verify pyproject.toml contents
    pyproject = (project_dir / "pyproject.toml").read_text()
    assert "[tool.belay]" in pyproject
    assert 'name = "my-project"' in pyproject


def test_new_creates_project_in_current_directory(tmp_cwd):
    """Test that belay new with no argument creates project in current directory."""
    new()

    assert (tmp_cwd / "pyproject.toml").exists()
    assert (tmp_cwd / "main.py").exists()

    # Package name should be derived from directory name
    pyproject = (tmp_cwd / "pyproject.toml").read_text()
    assert "[tool.belay]" in pyproject


def test_new_creates_project_with_dot_path(tmp_cwd):
    """Test that belay new . creates project in current directory."""
    new(".")

    assert (tmp_cwd / "pyproject.toml").exists()
    assert (tmp_cwd / "main.py").exists()


def test_new_adds_belay_sections_to_existing_pyproject(tmp_cwd):
    """Test that belay new adds belay sections to existing pyproject.toml."""
    existing_content = '[project]\nname = "existing-project"\nversion = "1.0.0"\n'
    (tmp_cwd / "pyproject.toml").write_text(existing_content)

    new()

    pyproject = (tmp_cwd / "pyproject.toml").read_text()
    # Original content preserved
    assert "[project]" in pyproject
    assert 'name = "existing-project"' in pyproject
    # Belay sections added
    assert "[tool.belay]" in pyproject
    assert "[tool.belay.dependencies]" in pyproject
    assert "[tool.pytest.ini_options]" in pyproject
    # Template files NOT copied
    assert not (tmp_cwd / "main.py").exists()
    assert not (tmp_cwd / "README.md").exists()


def test_new_merges_with_existing_pytest_section(tmp_cwd):
    """Test that belay new adds pythonpath to existing pytest configuration."""
    existing_content = dedent(
        """\
        [project]
        name = "existing-project"

        [tool.pytest.ini_options]
        testpaths = ["tests"]
        addopts = "-v"
        """
    )
    (tmp_cwd / "pyproject.toml").write_text(existing_content)

    new()

    pyproject = (tmp_cwd / "pyproject.toml").read_text()
    # Belay sections added
    assert "[tool.belay]" in pyproject
    assert "[tool.belay.dependencies]" in pyproject
    # Existing pytest settings preserved
    assert 'testpaths = ["tests"]' in pyproject
    assert 'addopts = "-v"' in pyproject
    # pythonpath added to existing pytest section
    assert 'pythonpath = ".belay/dependencies/main"' in pyproject


def test_new_adds_belay_deps_to_existing_pythonpath_string(tmp_cwd):
    """Test that belay new adds belay deps to existing string pythonpath."""
    existing_content = dedent(
        """\
        [project]
        name = "existing-project"

        [tool.pytest.ini_options]
        pythonpath = "src"
        """
    )
    (tmp_cwd / "pyproject.toml").write_text(existing_content)

    new()

    pyproject = (tmp_cwd / "pyproject.toml").read_text()
    # Existing pythonpath preserved and belay deps added
    assert "src" in pyproject
    assert ".belay/dependencies/main" in pyproject


def test_new_adds_belay_deps_to_existing_pythonpath_list(tmp_cwd):
    """Test that belay new adds belay deps to existing list pythonpath."""
    existing_content = dedent(
        """\
        [project]
        name = "existing-project"

        [tool.pytest.ini_options]
        pythonpath = ["src", "lib"]
        """
    )
    (tmp_cwd / "pyproject.toml").write_text(existing_content)

    new()

    pyproject = (tmp_cwd / "pyproject.toml").read_text()
    # Existing pythonpath preserved and belay deps added
    assert "src" in pyproject
    assert "lib" in pyproject
    assert ".belay/dependencies/main" in pyproject


def test_new_does_not_duplicate_belay_deps_in_pythonpath(tmp_cwd):
    """Test that belay new doesn't add duplicate belay deps to pythonpath."""
    existing_content = dedent(
        """\
        [project]
        name = "existing-project"

        [tool.pytest.ini_options]
        pythonpath = ["src", ".belay/dependencies/main"]
        """
    )
    (tmp_cwd / "pyproject.toml").write_text(existing_content)

    new()

    pyproject = (tmp_cwd / "pyproject.toml").read_text()
    # Should only appear once
    assert pyproject.count(".belay/dependencies/main") == 1


def test_new_errors_if_belay_already_configured(tmp_cwd):
    """Test that belay new errors if [tool.belay] already exists."""
    existing_content = dedent(
        """\
        [project]
        name = "existing-project"

        [tool.belay]
        name = "existing-project"
        """
    )
    (tmp_cwd / "pyproject.toml").write_text(existing_content)

    with pytest.raises(ValueError, match="already configured"):
        new()


def test_new_errors_if_belay_configured_in_target_dir(tmp_cwd):
    """Test that belay new errors if [tool.belay] exists in target directory."""
    target_dir = tmp_cwd / "existing-project"
    target_dir.mkdir()
    (target_dir / "pyproject.toml").write_text("[tool.belay]\nname = 'existing'\n")

    with pytest.raises(ValueError, match="already configured"):
        new("existing-project")


def test_new_canonicalizes_package_name(tmp_cwd):
    """Test that package names are canonicalized."""
    new("My_Project")

    project_dir = tmp_cwd / "My_Project"
    pyproject = (project_dir / "pyproject.toml").read_text()
    # packaging.utils.canonicalize_name converts to lowercase and replaces _ with -
    assert 'name = "my-project"' in pyproject
    assert (project_dir / "my-project" / "__init__.py").exists()


def test_new_canonicalizes_package_name_for_existing_project(tmp_cwd, monkeypatch):
    """Test that package names are canonicalized when adding to existing project."""
    # Create a directory with unusual name
    project_dir = tmp_cwd / "My_Weird_Project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)
    (project_dir / "pyproject.toml").write_text("[project]\nname = 'my-project'\n")

    new()

    pyproject = (project_dir / "pyproject.toml").read_text()
    assert 'name = "my-weird-project"' in pyproject
