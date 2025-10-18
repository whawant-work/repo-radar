"""repo-radar package initialization.

Exposes public API for configuration loading.
"""

__version__ = "0.1.0"

from .config import (
    Config,
    EmailConfig,
    GhPagesConfig,
    GithubAuth,
    LoadOptions,
    RepoRadarConfigError,
    load_config,
)
from .digest import build_digest
from .github_client import GitHubAPIError, GitHubClient
from .logging import SecretFilter, mask_secrets, setup_logging

__all__ = [
    "__version__",
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
    "build_digest",
]
