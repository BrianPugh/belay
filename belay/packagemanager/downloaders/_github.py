"""GitHub URL handling for package downloads."""

import re
from dataclasses import dataclass

from belay.packagemanager.downloaders.git import GitProviderUrl


@dataclass
class GitHubUrl(GitProviderUrl):
    """Parsed GitHub URL (shorthand or full HTTPS)."""

    # Patterns for full HTTPS URLs
    https_patterns = (
        re.compile(r"github\.com/(.+?)/(.+?)/blob/(.+?)/(.*)"),  # blob view
        re.compile(r"github\.com/(.+?)/(.+?)/tree/(.+?)/(.*)"),  # tree view
        re.compile(r"raw\.githubusercontent\.com/(.+?)/(.+?)/(.+?)/(.*)"),  # raw
    )

    @property
    def scheme(self) -> str:
        return "github"

    @property
    def raw_url(self) -> str:
        """Raw content URL at raw.githubusercontent.com."""
        base = f"https://raw.githubusercontent.com/{self.user}/{self.repo}/{self.branch}"
        return f"{base}/{self.path}" if self.path else base
