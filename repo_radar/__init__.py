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

__all__ = [
    "Config",
    "EmailConfig",
    "GhPagesConfig",
    "GithubAuth",
    "LoadOptions",
    "RepoRadarConfigError",
    "load_config",
]
