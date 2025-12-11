# isort: skip_file
# Import order matters: GitProviderUrl must be imported before subclasses
from .common import (
    NonMatchingURI,
    download_uri,
)
from .git import (
    GitProviderUrl,
    InvalidGitUrlError,
    rewrite_url,
)

# Import subclasses to register them with the Registry.
# These must be imported AFTER GitProviderUrl to ensure proper registration.
from ._github import GitHubUrl
from ._gitlab import GitLabUrl

__all__ = [
    "GitHubUrl",
    "GitLabUrl",
    "GitProviderUrl",
    "InvalidGitUrlError",
    "NonMatchingURI",
    "download_uri",
    "rewrite_url",
]
