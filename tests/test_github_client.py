from __future__ import annotations

import logging
from typing import Any

import pytest

from repo_radar.github_client import GitHubAPIError, GitHubClient


class DummyResp:
    def __init__(
        self,
        status_code: int,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = headers or {"Content-Type": "application/json"}
        self.text = text

    def json(self) -> dict[str, Any]:
        return self._json


def test_get_repo_success_injects_auth_and_logs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    captured_headers: dict[str, str] = {}

    def fake_request(
        method: str,
        url: str,
        headers: dict[str, str],
        params: dict[str, Any] | None,
        json: dict[str, Any] | None,
        timeout: int,
    ) -> DummyResp:  # type: ignore[override]
        captured_headers.update(headers)
        return DummyResp(
            200,
            {"full_name": "ok/repo"},
            headers={"X-RateLimit-Remaining": "4999"},
        )

    import repo_radar.github_client as mod

    monkeypatch.setattr(mod.requests, "request", fake_request)

    caplog.set_level(logging.INFO)
    client = GitHubClient(token="ghp_secret_token_123456")
    data = client.get_repo("ok", "repo")

    assert data["full_name"] == "ok/repo"
    # Authorization header is added
    assert captured_headers.get("Authorization", "").startswith("Bearer ")
    # Masked token appears in logs (not full token)
    log_text = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "ghp_" in log_text  # prefix shows
    assert "***" in log_text
    assert "secret_token" not in log_text


def test_error_raises_github_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_request(*args: Any, **kwargs: Any) -> DummyResp:  # type: ignore[no-untyped-def]
        return DummyResp(403, {"message": "forbidden"})

    import repo_radar.github_client as mod

    monkeypatch.setattr(mod.requests, "request", fake_request)
    client = GitHubClient(token=None)
    with pytest.raises(GitHubAPIError) as ei:
        client.get_repo("private", "repo")
    assert "403" in str(ei.value)
    assert "forbidden" in str(ei.value)

