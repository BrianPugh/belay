import pydantic
import pytest

from belay.packagemanager import GroupConfig
from belay.packagemanager.models import DependencySourceConfig, _is_git_like


def test_group_config_multiple_rename_to_init():
    dependencies = {
        "package": [
            {"uri": "foo", "rename_to_init": True},
            {"uri": "bar", "rename_to_init": True},
        ]
    }
    with pytest.raises(pydantic.ValidationError):
        GroupConfig(dependencies=dependencies)


@pytest.mark.parametrize(
    "uri",
    [
        "git://host.xz/path/to/repo.git/",
        "git://host.xz/~user/path/to/repo.git/",
        "git@host.xz:/path/to/repo.git/",
        "git@host.xz:path/to/repo.git",
        "git@host.xz:~user/path/to/repo.git/",
        "http://host.xz/path/to/repo.git/",
        "https://host.xz/path/to/repo.git/",
        "ssh://host.xz/path/to/repo.git/",
        "ssh://host.xz/path/to/repo.git/",
        "ssh://host.xz/~/path/to/repo.git",
        "ssh://host.xz/~user/path/to/repo.git/",
        "ssh://host.xz:port/path/to/repo.git/",
        "ssh://user@host.xz/path/to/repo.git/",
        "ssh://user@host.xz/path/to/repo.git/",
        "ssh://user@host.xz/~/path/to/repo.git",
        "ssh://user@host.xz/~user/path/to/repo.git/",
        "ssh://user@host.xz:port/path/to/repo.git/",
        "user@host.xz:/path/to/repo.git/",
        "user@host.xz:path/to/repo.git",
        "user@host.xz:~user/path/to/repo.git/",
        "git@github.com:BrianPugh/belay.git",
        "https://github.com/BrianPugh/belay.git",
    ],
)
def test_is_git_like(uri):
    assert _is_git_like(uri)


@pytest.mark.parametrize(
    "uri",
    [
        "https://www.google.com",
        "www.google.com",
        "google.com",
        "https://github.com/BrianPugh/belay",
    ],
)
def test_not_is_git_like(uri):
    assert not _is_git_like(uri)
