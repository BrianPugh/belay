"""GitHub URL handling for package downloads."""

import re
from dataclasses import dataclass
from typing import Optional

from belay.packagemanager.downloaders.git import GitProviderUrl


@dataclass
class GitHubUrl(GitProviderUrl):
    """Parsed GitHub URL (shorthand or full HTTPS)."""

    # Patterns for full HTTPS URLs (4 groups: user, repo, branch, path)
    https_patterns = (
        re.compile(r"github\.com/(.+?)/(.+?)/blob/(.+?)/(.*)"),  # blob view
        re.compile(r"github\.com/(.+?)/(.+?)/tree/(.+?)/(.*)"),  # tree view
        re.compile(r"raw\.githubusercontent\.com/(.+?)/(.+?)/(.+?)/(.*)"),  # raw
    )

    # Pattern for repo root URLs (2 groups: user, repo only)
    _repo_root_pattern = re.compile(r"github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")

    @classmethod
    def _parse_https(cls, url: str) -> Optional["GitHubUrl"]:
        """Parse full HTTPS URL, including repo root URLs.

        Extends base class to handle repo root URLs like
        ``https://github.com/user/repo`` which don't have blob/tree paths.
        """
        # Try standard patterns first (4 groups: user, repo, branch, path)
        result = super()._parse_https(url)
        if result is not None:
            return result

        # Try repo root pattern (2 groups: user, repo)
        match = cls._repo_root_pattern.search(url)
        if match:
            user, repo = match.groups()
            return cls(user=user, repo=repo, path="", branch="HEAD")

        return None

    @property
    def scheme(self) -> str:
        return "github"

    @property
    def raw_url(self) -> str:
        """Raw content URL at raw.githubusercontent.com."""
        base = f"https://raw.githubusercontent.com/{self.user}/{self.repo}/{self.branch}"
        return f"{base}/{self.path}" if self.path else base
