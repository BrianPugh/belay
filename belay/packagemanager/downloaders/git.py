"""Base class for git provider URL handling."""

import logging
import shutil
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import git
from autoregistry import Registry

from belay.packagemanager.downloaders._retry import fetch_url

__all__ = [
    "GitProviderUrl",
    "InvalidGitUrlError",
    "rewrite_url",
    "split_version_suffix",
]

logger = logging.getLogger(__name__)


class InvalidGitUrlError(Exception):
    """URL is not a recognized git provider URL (GitHub, GitLab, etc.)."""


def split_version_suffix(uri: str) -> tuple[str, Optional[str]]:
    """Split URI into base and version suffix.

    Extracts version suffix from URIs, supporting both ``@version`` and
    ``==version`` syntax. Correctly handles HTTP URLs that may contain
    @ in userinfo (e.g., https://user@host/path).

    Parameters
    ----------
    uri
        URI that may contain version suffix.

    Returns
    -------
    tuple[str, Optional[str]]
        (base_uri, version) where version is None if not present.

    Examples
    --------
    >>> split_version_suffix("aiohttp@1.0.0")
    ('aiohttp', '1.0.0')
    >>> split_version_suffix("aiohttp==1.0.0")
    ('aiohttp', '1.0.0')
    >>> split_version_suffix("github:user/repo@v1.0")
    ('github:user/repo', 'v1.0')
    >>> split_version_suffix("https://example.com/file.py")
    ('https://example.com/file.py', None)
    >>> split_version_suffix("aiohttp")
    ('aiohttp', None)
    """
    # Don't split on @ for http(s) URLs (they may have @ in userinfo)
    if uri.startswith(("http://", "https://")):
        return uri, None
    # Support == syntax (pip-style)
    if "==" in uri:
        base, version = uri.rsplit("==", 1)
        return base, version
    # Support @ syntax
    if "@" in uri:
        base, version = uri.rsplit("@", 1)
        return base, version
    return uri, None


@dataclass
class GitProviderUrl(Registry, suffix="Url"):
    """Base class for parsed git provider URLs.

    Subclasses implement provider-specific URL parsing and downloading.
    Use :meth:`parse` to create instances - it automatically selects the
    appropriate subclass based on the URL scheme or domain.

    Attributes
    ----------
    user
        The user or organization name.
    repo
        The repository name.
    path
        The path within the repository (may be empty).
    branch
        The branch/tag/ref (from @suffix or default).
    """

    user: str
    repo: str
    path: str
    branch: str

    # Regex patterns to match full HTTPS URLs - subclasses override
    https_patterns: tuple = ()

    @property
    @abstractmethod
    def scheme(self) -> str:
        """URL scheme identifier (e.g., 'github', 'gitlab')."""

    @classmethod
    def parse(cls, url: str, default_branch: str = "HEAD") -> "GitProviderUrl":
        """Parse a shorthand or full URL into the appropriate provider-specific instance.

        Supports both shorthand syntax (e.g., ``github:user/repo/path@branch``)
        and full HTTPS URLs (e.g., ``https://github.com/user/repo/blob/main/path``).

        Parameters
        ----------
        url
            URL to parse (shorthand or full HTTPS).
        default_branch
            Branch to use if not specified in URL.

        Returns
        -------
        GitProviderUrl
            Parsed URL as provider-specific subclass.

        Raises
        ------
        InvalidGitUrlError
            If the URL is not a recognized git provider URL.
        ValueError
            If the URL is recognized but has invalid format.

        Examples
        --------
        >>> GitProviderUrl.parse("github:user/repo/file.py@main")
        GitHubUrl(user='user', repo='repo', path='file.py', branch='main')

        >>> GitProviderUrl.parse("https://github.com/user/repo/blob/main/file.py")
        GitHubUrl(user='user', repo='repo', path='file.py', branch='main')
        """
        parsed = urlparse(url)

        # Try shorthand syntax first (github:, gitlab:, etc.)
        try:
            url_class = cls[parsed.scheme]
            return url_class._parse_shorthand(url, default_branch)
        except KeyError:
            pass

        # Try full HTTPS URLs by checking each provider's patterns
        if parsed.scheme in ("http", "https"):
            for url_class in cls.values():
                result = url_class._parse_https(url)
                if result is not None:
                    return result

        raise InvalidGitUrlError(f"Not a recognized git provider URL: {url}")

    @classmethod
    def _parse_shorthand(cls, url: str, default_branch: str) -> "GitProviderUrl":
        """Parse shorthand URL (e.g., github:user/repo/path@branch)."""
        parsed = urlparse(url)
        path = parsed.path
        branch = default_branch

        # Extract branch if specified with @
        if "@" in path:
            path, branch = path.rsplit("@", 1)

        # Parse user/repo/file_path
        parts = path.split("/", 2)
        if len(parts) < 2:
            raise ValueError(f"Invalid {parsed.scheme} URL: {url} (expected {parsed.scheme}:user/repo[/path])")

        user, repo = parts[0], parts[1]
        file_path = parts[2] if len(parts) > 2 else ""

        return cls(user=user, repo=repo, path=file_path, branch=branch)

    @classmethod
    def _parse_https(cls, url: str) -> Optional["GitProviderUrl"]:
        """Parse full HTTPS URL using https_patterns."""
        for pattern in cls.https_patterns:
            match = pattern.search(url)
            if match:
                user, repo, branch, path = match.groups()
                return cls(user=user, repo=repo, path=path, branch=branch)
        return None

    @property
    def canonical_id(self) -> str:
        """Return canonical identifier (user/repo) for deduplication."""
        return f"{self.user}/{self.repo}".lower()

    @property
    def inferred_package_name(self) -> str:
        """Infer a package name from this URL's path or repo.

        Returns the last component of the path if present, otherwise
        the repository name. Does not sanitize the name (caller should
        handle conversion to valid Python identifier if needed).

        Returns
        -------
        str
            Inferred package name (may need sanitization).

        Examples
        --------
        >>> url = GitProviderUrl.parse("github:user/repo/path/module.py")
        >>> url.inferred_package_name
        'module.py'
        >>> url = GitProviderUrl.parse("github:user/my-repo")
        >>> url.inferred_package_name
        'my-repo'
        """
        if self.path:
            return self.path.rstrip("/").split("/")[-1]
        return self.repo

    @property
    @abstractmethod
    def raw_url(self) -> str:
        """Raw content URL for downloading."""

    def has_file_extension(self) -> bool:
        """Check if path appears to have a file extension.

        Returns True if the last path component contains a dot that is not
        at the start (to exclude hidden directories like '.github').

        Returns
        -------
        bool
            True if path appears to have a file extension.
        """
        if not self.path:
            return False
        last_part = self.path.rsplit("/", 1)[-1]
        dot_pos = last_part.rfind(".")
        return dot_pos > 0

    @property
    def repo_url(self) -> str:
        """Git clone URL for this repository."""
        return f"https://{self.scheme}.com/{self.user}/{self.repo}.git"

    @property
    def cache_prefix(self) -> str:
        """Prefix for cache folder name."""
        return f"git-{self.scheme}"

    def download(self, dst: Path) -> Path:
        """Download file or folder to destination.

        Tries to download as a single file first. If that fails (404),
        falls back to cloning the repository and copying the path.

        Parameters
        ----------
        dst
            Destination directory.

        Returns
        -------
        Path
            Path to downloaded file or folder.

        Raises
        ------
        requests.exceptions.RequestException
            If download fails after retries.
        git.exc.GitCommandError
            If git clone/pull/checkout fails.
        """
        r = fetch_url(self.raw_url)

        if r.status_code == 200:
            # Single file download
            if self.path:
                dst = dst / Path(self.path).name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(r.content)
        elif r.status_code == 404:
            # Probably a folder - clone repo and copy
            self._clone_and_copy(dst)
        else:
            r.raise_for_status()

        return dst

    def _clone_and_copy(self, dst: Path) -> None:
        """Clone repository and copy path to destination.

        Parameters
        ----------
        dst
            Destination directory.

        Raises
        ------
        git.exc.GitCommandError
            If git operations fail.
        """
        from belay.project import find_cache_folder

        repo_folder = find_cache_folder() / f"{self.cache_prefix}-{self.user}-{self.repo}"
        repo_folder.mkdir(exist_ok=True, parents=True)

        try:
            if (repo_folder / ".git").is_dir():
                repo = git.Repo(repo_folder)
                try:
                    repo.remotes.origin.fetch()
                except git.exc.GitCommandError as e:
                    # If fetch fails, try to continue with existing state
                    logger.warning(f"Failed to fetch updates for {self.repo_url}: {e}. Using cached version.")
            else:
                repo = git.Repo.clone_from(self.repo_url, repo_folder)

            # Clean and checkout the specific branch/tag
            repo.git.clean("-xdf")
            repo.git.checkout(self.branch)

        except git.exc.GitCommandError as e:
            # Re-raise with more context
            raise git.exc.GitCommandError(
                e.command,
                e.status,
                stderr=f"Failed to clone/checkout {self.repo_url}@{self.branch}: {e.stderr}",
            ) from e

        if self.path:
            shutil.copytree(repo_folder / self.path, dst, dirs_exist_ok=True)
        else:
            shutil.copytree(repo_folder, dst, dirs_exist_ok=True)


def rewrite_url(url: str, branch: str = "HEAD") -> str:
    """Rewrite github: or gitlab: shorthand to full URLs.

    For URLs with unrecognized schemes (http://, https://, etc.), returns the
    original URL unchanged. For recognized git provider schemes (github:, gitlab:),
    parses and rewrites to full URLs.

    Parameters
    ----------
    url
        URL that may use shorthand syntax.
    branch
        Default branch if not specified in URL.

    Returns
    -------
    str
        Full HTTP(S) URL, or the original URL if not a git provider URL.

    Raises
    ------
    ValueError
        If URL uses a recognized git provider scheme (github:, gitlab:) but
        has invalid format (e.g., missing user/repo).

    Examples
    --------
    >>> rewrite_url("github:user/repo/path/file.py")
    'https://raw.githubusercontent.com/user/repo/HEAD/path/file.py'

    >>> rewrite_url("github:user/repo/path/file.py@main")
    'https://raw.githubusercontent.com/user/repo/main/path/file.py'

    >>> rewrite_url("gitlab:user/repo/path/file.py@develop")
    'https://gitlab.com/user/repo/-/raw/develop/path/file.py'

    >>> rewrite_url("https://example.com/file.py")
    'https://example.com/file.py'
    """
    try:
        parsed = GitProviderUrl.parse(url, default_branch=branch)
    except InvalidGitUrlError:
        return url
    return parsed.raw_url
