from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

import requests


class GitHubAPIError(RuntimeError):
    """Raised when GitHub API returns a non-success status code.

    Attributes:
        status_code: HTTP status code of the response
        error: Parsed error message from the response body, if any
    """

    def __init__(self, status_code: int, error: str | None = None) -> None:
        msg = f"GitHub API error: {status_code}"
        if error:
            msg = f"{msg} - {error}"
        super().__init__(msg)
        self.status_code = status_code
        self.error = error


def _mask_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}***{value[-4:]}"


class GitHubClient:
    """Minimal GitHub REST client wrapper.

    - Adds PAT Authorization header when token is provided
    - Logs request/response with token masked
    - Logs rate-limit headers (limit/remaining/reset)
    - Raises GitHubAPIError for non-2xx responses
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        base_url: str = "https://api.github.com",
        timeout: int = 15,
        logger: logging.Logger | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout
        self._log = logger or logging.getLogger("repo_radar.github_client")

    # Public helpers -----------------------------------------------------
    def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        return self._request_json("GET", f"/repos/{owner}/{repo}")

    # Core request -------------------------------------------------------
    def _build_headers(self, extra: Mapping[str, str] | None = None) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if extra:
            headers.update(extra)
        return headers

    def _log_rate_limit(self, headers: Mapping[str, str]) -> None:
        limit = headers.get("X-RateLimit-Limit")
        remaining = headers.get("X-RateLimit-Remaining")
        reset = headers.get("X-RateLimit-Reset")
        if limit or remaining or reset:
            self._log.info(
                "GitHub rate limit: remaining=%s / limit=%s reset=%s",
                remaining,
                limit,
                reset,
            )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        body: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        if not path.startswith("/"):
            path = "/" + path
        url = f"{self._base_url}{path}"

        masked_auth = _mask_secret(self._token)
        self._log.info("GitHub %s %s (auth=%s)", method, path, masked_auth or "<none>")

        resp = requests.request(
            method,
            url,
            headers=self._build_headers(headers or {}),
            params=dict(params) if params else None,
            json=dict(body) if body else None,
            timeout=self._timeout,
        )

        self._log_rate_limit(resp.headers)

        if 200 <= resp.status_code < 300:
            if resp.headers.get("Content-Type", "").startswith("application/json"):
                return resp.json()  # type: ignore[return-value]
            # Fallback: try parse JSON, otherwise wrap as text
            try:
                return resp.json()  # type: ignore[return-value]
            except Exception:
                return {"raw": resp.text}

        # Build readable error message
        error_message: str | None = None
        try:
            data = resp.json()
            if isinstance(data, dict) and "message" in data:
                error_message = str(data.get("message"))
            else:
                error_message = json.dumps(data, ensure_ascii=False)
        except Exception:
            if resp.text:
                error_message = resp.text[:500]

        raise GitHubAPIError(resp.status_code, error_message)


__all__ = ["GitHubClient", "GitHubAPIError"]
