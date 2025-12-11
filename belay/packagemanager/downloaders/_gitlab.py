"""GitLab URL handling for package downloads."""

import re
from dataclasses import dataclass

from belay.packagemanager.downloaders.git import GitProviderUrl


@dataclass
class GitLabUrl(GitProviderUrl):
    """Parsed GitLab URL (shorthand or full HTTPS)."""

    # Patterns for full HTTPS URLs
    https_patterns = (
        re.compile(r"gitlab\.com/(.+?)/(.+?)/-/raw/(.+?)/(.*)"),  # raw
        re.compile(r"gitlab\.com/(.+?)/(.+?)/-/blob/(.+?)/(.*)"),  # blob view
        re.compile(r"gitlab\.com/(.+?)/(.+?)/-/tree/(.+?)/(.*)"),  # tree view
    )

    @property
    def scheme(self) -> str:
        return "gitlab"

    @property
    def raw_url(self) -> str:
        """Raw content URL at gitlab.com."""
        base = f"https://gitlab.com/{self.user}/{self.repo}/-/raw/{self.branch}"
        return f"{base}/{self.path}" if self.path else base
