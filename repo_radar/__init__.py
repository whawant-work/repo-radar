"""repo-radar package initialization.

Exposes public API for configuration loading.
"""

from .config import (
    Config,
    EmailConfig,
    GhPagesConfig,
    GithubAuth,
    LoadOptions,
    RepoRadarConfigError,
    load_config,
)
from .github_client import GitHubAPIError, GitHubClient
from .logging import SecretFilter, mask_secrets, setup_logging

__all__ = [
    "Config",
    "EmailConfig",
    "GhPagesConfig",
    "GithubAuth",
    "LoadOptions",
    "RepoRadarConfigError",
    "load_config",
    "GitHubClient",
    "GitHubAPIError",
    "setup_logging",
    "SecretFilter",
    "mask_secrets",
]
