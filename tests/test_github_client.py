from __future__ import annotations

import logging
from typing import Any

import pytest

from repo_radar.github_client import GitHubAPIError, GitHubClient


class DummyResp:
    def __init__(
        self,
        status_code: int,
        json_data: Any | None = None,
        headers: dict[str, str] | None = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._json = {} if json_data is None else json_data
        self.headers = headers or {"Content-Type": "application/json"}
        self.text = text

    def json(self) -> Any:
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


def test_iter_json_list_paginates_with_link(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_request(
        method: str,
        url: str,
        headers: dict[str, str],
        params: dict[str, Any] | None,
        json: dict[str, Any] | None,
        timeout: int,
    ) -> DummyResp:  # type: ignore[override]
        calls.append(url)
        if "page=1" in url:
            return DummyResp(
                200,
                json_data=[{"id": 1}, {"id": 2}],
                headers={
                    "Content-Type": "application/json",
                    "Link": "<https://api.github.com/foo?page=2>; rel=\"next\"",
                },
            )
        if "page=2" in url:
            return DummyResp(
                200, json_data=[{"id": 3}], headers={"Content-Type": "application/json"}
            )
        # absolute next URL path
        if url.endswith("/foo") and "page=2" not in url:
            return DummyResp(
                200, json_data=[{"id": 3}], headers={"Content-Type": "application/json"}
            )
        return DummyResp(404, json_data={"message": "not found"})

    import repo_radar.github_client as mod

    monkeypatch.setattr(mod.requests, "request", fake_request)
    client = GitHubClient()
    items = list(client.iter_json_list("/foo", params={"page": 1, "per_page": 2}))
    assert [x["id"] for x in items] == [1, 2, 3]
    assert any("page=1" in c for c in calls)
    assert any("page=2" in c for c in calls)


def test_request_retries_on_5xx(monkeypatch: pytest.MonkeyPatch) -> None:
    sequence = [500, 502, 200]
    attempts: list[int] = []

    def fake_sleep(sec: float) -> None:  # no-op to speed tests
        return None

    def fake_request(
        method: str,
        url: str,
        headers: dict[str, str],
        params: dict[str, Any] | None,
        json: dict[str, Any] | None,
        timeout: int,
    ) -> DummyResp:  # type: ignore[override]
        attempts.append(1)
        code = sequence.pop(0)
        return DummyResp(code, json_data={"ok": True})

    import repo_radar.github_client as mod

    monkeypatch.setattr(mod.requests, "request", fake_request)
    monkeypatch.setattr(mod.time, "sleep", fake_sleep)
    client = GitHubClient()
    data = client._request_json("GET", "/any")
    assert data["ok"] is True
    # should have retried twice before success
    assert len(attempts) == 3


def test_request_retry_network_error_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class NetError(Exception):
        pass

    attempts = {"n": 0}

    def fake_sleep(sec: float) -> None:
        return None

    def fake_request(
        method: str,
        url: str,
        headers: dict[str, str],
        params: dict[str, Any] | None,
        json: dict[str, Any] | None,
        timeout: int,
    ):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise mod.requests.RequestException("boom")
        return DummyResp(200, json_data={"ok": True})

    import repo_radar.github_client as mod

    monkeypatch.setattr(mod.requests, "request", fake_request)
    monkeypatch.setattr(mod.time, "sleep", fake_sleep)
    client = GitHubClient()
    data = client._request_json("GET", "/ok")
    assert data["ok"] is True
    assert attempts["n"] == 2


def test_request_retry_exceeds_then_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_sleep(sec: float) -> None:
        return None

    def fake_request(
        method: str,
        url: str,
        headers: dict[str, str],
        params: dict[str, Any] | None,
        json: dict[str, Any] | None,
        timeout: int,
    ):
        raise mod.requests.RequestException("no network")

    import repo_radar.github_client as mod

    monkeypatch.setattr(mod.requests, "request", fake_request)
    monkeypatch.setattr(mod.time, "sleep", fake_sleep)
    client = GitHubClient()
    with pytest.raises(GitHubAPIError) as ei:
        client._request_json("GET", "/fail")
    assert "network error after retries" in str(ei.value)
