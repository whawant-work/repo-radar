from __future__ import annotations

import os

from .github_client import GitHubAPIError, GitHubClient


def resolve_me(
    *,
    cli_me: str | None = None,
    env_me: str | None = None,
    github_client: GitHubClient | None = None,
) -> str | None:
    """Resolve current user login using a priority chain.

    Priority: CLI --me > env/config ME_LOGIN > GitHub /user > GITHUB_ACTOR > None
    """
    # 1) CLI overrides everything
    if cli_me and cli_me.strip():
        return cli_me.strip()

    # 2) Explicit env/config
    if env_me and env_me.strip():
        return env_me.strip()

    # 3) GitHub /user (if client present and token likely configured)
    if github_client is not None:
        try:
            user = github_client.get_current_user()
            login = (user.get("login") if isinstance(user, dict) else None) or None
            if login and str(login).strip():
                return str(login).strip()
        except GitHubAPIError:
            # Swallow and continue to next source
            pass
        except Exception:
            pass

    # 4) GitHub Actions actor (fallback)
    gha = os.environ.get("GITHUB_ACTOR")
    if gha and gha.strip():
        return gha.strip()

    # None if we couldn't determine
    return None


__all__ = ["resolve_me"]
