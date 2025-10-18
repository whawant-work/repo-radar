from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Iterator, Mapping
from typing import Any

import requests
from requests import Response


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
        # retry settings (Issue #8)
        self._max_retries = 5
        self._backoff_schedule = [1, 2, 4, 8]  # seconds; length max_retries-1

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
        resp = self._request(
            method,
            path,
            params=params,
            body=body,
            headers=headers,
        )

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

    # Retry-capable raw request ----------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        body: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Response:
        # Allow absolute URL (for Link: rel="next"); otherwise build from base + path
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            if not path.startswith("/"):
                path = "/" + path
            url = f"{self._base_url}{path}"

        # For deterministic testing and logging, embed query params directly into URL
        if params:
            try:
                from requests.models import PreparedRequest

                pr = PreparedRequest()
                pr.prepare_url(url, dict(params))
                url = pr.url or url
                params = None
            except Exception:
                try:
                    from urllib.parse import urlencode

                    qs = urlencode(params, doseq=True)  # type: ignore[arg-type]
                    sep = "&" if ("?" in url) else "?"
                    url = f"{url}{sep}{qs}"
                    params = None
                except Exception:
                    # Fallback: keep params as-is; requests will handle
                    pass

        masked_auth = _mask_secret(self._token)
        self._log.info("GitHub %s %s (auth=%s)", method, url, masked_auth or "<none>")

        attempt = 0
        while True:
            attempt += 1
            try:
                resp = requests.request(
                    method,
                    url,
                    headers=self._build_headers(headers or {}),
                    params=dict(params) if params else None,
                    json=dict(body) if body else None,
                    timeout=self._timeout,
                )
                self._log_rate_limit(resp.headers)

                # Retry on 5xx
                if 500 <= resp.status_code < 600 and attempt < self._max_retries:
                    delay = self._calc_delay(resp, attempt)
                    self._log.warning(
                        "GitHub %s %s -> %s, retrying in %.1fs (attempt %d/%d)",
                        method,
                        path,
                        resp.status_code,
                        delay,
                        attempt,
                        self._max_retries,
                    )
                    time.sleep(delay)
                    continue

                return resp
            except requests.RequestException as exc:  # network-level
                if attempt < self._max_retries:
                    delay = self._backoff_schedule[
                        min(attempt - 1, len(self._backoff_schedule) - 1)
                    ]
                    self._log.warning(
                        "GitHub %s %s network error: %s, retrying in %.1fs (attempt %d/%d)",
                        method,
                        path,
                        exc,
                        delay,
                        attempt,
                        self._max_retries,
                    )
                    time.sleep(delay)
                    continue
                # Exceeded retries -> synthesize a 599 response-like error by raising
                raise GitHubAPIError(599, f"network error after retries: {exc}") from exc

    def _calc_delay(self, resp: Response, attempt: int) -> float:
        # Honor Retry-After if present and numeric seconds
        ra = resp.headers.get("Retry-After")
        if ra and ra.isdigit():
            try:
                sec = float(ra)
                if sec >= 0:
                    return sec
            except Exception:
                pass
        idx = min(attempt - 1, len(self._backoff_schedule) - 1)
        return float(self._backoff_schedule[idx])

    # Pagination --------------------------------------------------------
    _LINK_RE = re.compile(r"<([^>]+)>;\s*rel=\"(\w+)\"")

    def _parse_link_next(self, link_header: str | None) -> str | None:
        if not link_header:
            return None
        parts = link_header.split(",")
        for p in parts:
            m = self._LINK_RE.search(p)
            if m and m.group(2) == "next":
                return m.group(1)
        return None

    def iter_json_list(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        per_page: int = 100,
    ) -> Iterator[Any]:
        """Iterate all items from a paginated GitHub REST endpoint.

        - Uses Link header rel="next" if provided
        - Falls back to page/per_page parameters
        - Accepts either JSON array response or object with 'items' array (search API)
        """
        # First request with explicit per_page
        q = dict(params or {})
        if "per_page" not in q:
            q["per_page"] = per_page

        next_url: str | None = None
        page = 1
        while True:
            if next_url is None:
                q["page"] = page
                resp = self._request("GET", path, params=q)
            else:
                # Use absolute next URL directly to preserve query string (e.g., page=2)
                resp = self._request("GET", next_url)

            data: Any
            if resp.headers.get("Content-Type", "").startswith("application/json"):
                data = resp.json()
            else:
                try:
                    data = resp.json()
                except Exception as exc:  # pragma: no cover - safety
                    raise GitHubAPIError(resp.status_code, f"invalid JSON: {exc}") from exc

            # Success check
            if not (200 <= resp.status_code < 300):
                # Let _request_json logic format the error similarly
                error_message: str | None = None
                try:
                    d = resp.json()
                    if isinstance(d, dict) and "message" in d:
                        error_message = str(d.get("message"))
                except Exception:
                    pass
                raise GitHubAPIError(resp.status_code, error_message)

            # Determine items
            items: list[Any]
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict) and isinstance(data.get("items"), list):
                items = data["items"]
            else:
                # Not a list response
                raise GitHubAPIError(500, "expected a JSON list or an object with 'items'")

            yield from items

            # Check for next link
            next_url = self._parse_link_next(resp.headers.get("Link"))
            if next_url:
                page += 1
                continue
            # Fallback stop condition: if less than per_page, likely last page
            if len(items) < int(q.get("per_page", per_page)):
                break
            # If equal to per_page and no Link header, increment page (some APIs omit Link)
            page += 1


__all__ = ["GitHubClient", "GitHubAPIError"]
