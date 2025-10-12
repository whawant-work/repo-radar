from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

import requests


class RepoRegistryError(ValueError):
    """Raised when registry file or entries are invalid."""


_OWNER_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _is_owner_repo(s: str) -> bool:
    return bool(_OWNER_REPO_RE.fullmatch(s))


def _unique_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def load_repos(path: Path) -> list[str]:
    """Load repository list from a `.list` file.

    Rules:
    - One `owner/repo` per line
    - Lines starting with `#` or blank lines are ignored
    - Whitespace around entries is stripped
    - Duplicates are removed while preserving the first occurrence order

    On invalid format, raises RepoRegistryError with the faulty line number.
    """
    if not path.exists():
        raise RepoRegistryError(f"Registry file not found: {path}")

    entries: list[str] = []
    for idx, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Allow trailing inline comment using ` # ` syntax – only if preceded by space
        # e.g., owner/repo  # comment
        if " #" in line:
            line = line.split(" #", 1)[0].rstrip()
        if not _is_owner_repo(line):
            raise RepoRegistryError(
                f"Invalid repo format at line {idx}: '{raw}'. Expected 'owner/repo'"
            )
        entries.append(line)

    return _unique_preserve_order(entries)


def validate_repos(repos: list[str], github_token: str | None) -> dict[str, str]:
    """Validate repositories against GitHub API.

    Returns a dict of repo -> error_reason for those that fail validation.
    - 200: OK (no entry in result)
    - 404: Not found => "not found"
    - 401/403: Unauthorized/Forbidden => "unauthorized or forbidden"
    - others: "http {status_code}"
    Network errors are reported as "network error: {exc}".
    """
    errors: dict[str, str] = {}
    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    for r in repos:
        owner, name = r.split("/", 1)
        url = f"https://api.github.com/repos/{owner}/{name}"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
        except Exception as exc:  # pragma: no cover - exercised via unit test
            errors[r] = f"network error: {exc}"
            continue

        if resp.status_code == 200:
            continue
        if resp.status_code == 404:
            errors[r] = "not found"
        elif resp.status_code in (401, 403):
            errors[r] = "unauthorized or forbidden"
        else:
            errors[r] = f"http {resp.status_code}"

    return errors


__all__ = ["RepoRegistryError", "load_repos", "validate_repos"]
