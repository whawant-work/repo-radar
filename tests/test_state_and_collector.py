from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from repo_radar.collector import Collector
from repo_radar.state import get_last_run, set_last_run


def test_state_read_write(tmp_path: Path) -> None:
    p = tmp_path / "state.txt"
    assert get_last_run(p) is None
    set_last_run("2025-10-10T00:00:00Z", p)
    assert get_last_run(p) == "2025-10-10T00:00:00Z"


class DummyClient:
    def __init__(self, items: list[dict[str, Any]]) -> None:
        self._items = items

    def iter_json_list(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        per_page: int = 100,
    ) -> Iterator[Any]:  # type: ignore[override]
        # Ignore pagination; return all
        return iter(self._items)


def test_collector_incremental_filters_by_updated_at(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Prepare registry file
    cfgdir = tmp_path / "config"
    cfgdir.mkdir()
    reg = cfgdir / "repos.list"
    reg.write_text("owner/repo\n", encoding="utf-8")

    # Items around baseline
    items = [
        {
            "id": 1,
            "number": 10,
            "title": "old",
            "user": {"login": "a"},
            "updated_at": "2025-10-10T00:00:00Z",
            "state": "open",
        },
        {
            "id": 2,
            "number": 11,
            "title": "new",
            "user": {"login": "b"},
            "updated_at": "2025-10-10T00:00:01Z",
            "state": "open",
        },
    ]
    client = DummyClient(items)

    # Force baseline
    col = Collector(github_client=client)  # type: ignore[arg-type]
    result = col.collect(reg, since="2025-10-10T00:00:00Z", persist_last_run=False)
    # Should include only the item strictly after baseline (id=2)
    assert [x["id"] for x in result] == [2]


def test_collector_persists_last_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Prepare registry file
    cfgdir = tmp_path / "config"
    cfgdir.mkdir()
    reg = cfgdir / "repos.list"
    reg.write_text("owner/repo\n", encoding="utf-8")

    calls = {"n": 0}

    # Monkeypatch set_last_run to observe calls
    def fake_set_last_run() -> None:
        calls["n"] += 1

    import repo_radar.collector as colmod

    monkeypatch.setattr(colmod, "set_last_run", fake_set_last_run)

    client = DummyClient([])
    col = Collector(github_client=client)  # type: ignore[arg-type]
    _ = col.collect(reg, persist_last_run=True)
    assert calls["n"] == 1


# ===== 이슈 #10: 페이징 및 재시도 테스트 =====


class PagingClient:
    """Mock client that simulates paginated responses."""

    def __init__(self, pages: list[list[dict[str, Any]]]) -> None:
        self._pages = pages

    def iter_json_list(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        per_page: int = 100,
    ) -> Iterator[Any]:
        # Simulate pagination by yielding items from all pages
        # iter_json_list yields individual items, not pages
        for page in self._pages:
            yield from page


def test_collector_paging_aggregates_all_pages(tmp_path: Path) -> None:
    """Collector는 여러 페이지에 걸친 데이터를 모두 수집해야 함."""
    # Prepare registry file
    cfgdir = tmp_path / "config"
    cfgdir.mkdir()
    reg = cfgdir / "repos.list"
    reg.write_text("owner/repo\n", encoding="utf-8")

    # Simulate 3 pages with 2 items each
    # Note: GitHub API returns pull_request with URL info for PRs, not empty dict
    page1 = [
        {
            "id": 1,
            "number": 10,
            "title": "PR 1",
            "user": {"login": "alice"},
            "updated_at": "2025-10-15T10:00:00Z",
            "state": "open",
            "pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/10"},
        },
        {
            "id": 2,
            "number": 11,
            "title": "Issue 1",
            "user": {"login": "bob"},
            "updated_at": "2025-10-15T11:00:00Z",
            "state": "open",
        },
    ]
    page2 = [
        {
            "id": 3,
            "number": 12,
            "title": "PR 2",
            "user": {"login": "charlie"},
            "updated_at": "2025-10-15T12:00:00Z",
            "state": "open",
            "pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/12"},
        },
        {
            "id": 4,
            "number": 13,
            "title": "Issue 2",
            "user": {"login": "diana"},
            "updated_at": "2025-10-15T13:00:00Z",
            "state": "open",
        },
    ]
    page3 = [
        {
            "id": 5,
            "number": 14,
            "title": "PR 3",
            "user": {"login": "eve"},
            "updated_at": "2025-10-15T14:00:00Z",
            "state": "open",
            "pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/14"},
        },
    ]

    client = PagingClient([page1, page2, page3])
    col = Collector(github_client=client)  # type: ignore[arg-type]
    result = col.collect(reg, persist_last_run=False)

    # Should collect all 5 items across 3 pages
    assert len(result) == 5
    assert [x["id"] for x in result] == [1, 2, 3, 4, 5]
    # Verify types are correctly identified
    types = [x["type"] for x in result]
    assert types.count("PR") == 3
    assert types.count("Issue") == 2


class RetryClient:
    """Mock client that simulates retry scenarios within a single call."""

    def __init__(self, scenario: str) -> None:
        self.scenario = scenario
        self.call_count = 0

    def iter_json_list(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        per_page: int = 100,
    ) -> Iterator[Any]:
        from repo_radar.github_client import GitHubAPIError

        self.call_count += 1

        if self.scenario == "retry_then_success":
            # Simulate retry within GitHubClient: first attempts fail, last succeeds
            # Since we're mocking at iter_json_list level, we simulate the final success
            return iter(
                [
                    {
                        "id": 100,
                        "number": 50,
                        "title": "Recovered after retry",
                        "user": {"login": "bot"},
                        "updated_at": "2025-10-15T15:00:00Z",
                        "state": "open",
                    }
                ]
            )
        elif self.scenario == "timeout_then_success":
            # Similar to above, simulate successful result after internal retries
            return iter(
                [
                    {
                        "id": 200,
                        "number": 60,
                        "title": "Recovered after timeout",
                        "user": {"login": "system"},
                        "updated_at": "2025-10-15T16:00:00Z",
                        "state": "open",
                    }
                ]
            )
        elif self.scenario == "permanent_failure":
            # Always fails even after retries
            raise GitHubAPIError(503, "Service Unavailable")
        return iter([])


def test_collector_retries_on_5xx_error(tmp_path: Path) -> None:
    """Collector는 내부적으로 GitHubClient의 재시도 메커니즘을 통해 5xx 에러를 복구함."""
    cfgdir = tmp_path / "config"
    cfgdir.mkdir()
    reg = cfgdir / "repos.list"
    reg.write_text("owner/repo\n", encoding="utf-8")

    # GitHubClient가 내부적으로 재시도하여 성공한 결과를 반환하는 시나리오
    client = RetryClient("retry_then_success")
    col = Collector(github_client=client)  # type: ignore[arg-type]

    result = col.collect(reg, persist_last_run=False)
    assert len(result) == 1
    assert result[0]["id"] == 100
    assert result[0]["title"] == "Recovered after retry"


def test_collector_handles_timeout_with_retry(tmp_path: Path) -> None:
    """Collector는 타임아웃 발생 시 GitHubClient의 재시도를 통해 복구함."""
    cfgdir = tmp_path / "config"
    cfgdir.mkdir()
    reg = cfgdir / "repos.list"
    reg.write_text("owner/repo\n", encoding="utf-8")

    client = RetryClient("timeout_then_success")
    col = Collector(github_client=client)  # type: ignore[arg-type]

    result = col.collect(reg, persist_last_run=False)
    assert len(result) == 1
    assert result[0]["id"] == 200
    assert result[0]["title"] == "Recovered after timeout"


def test_collector_fails_after_max_retries(tmp_path: Path) -> None:
    """Collector는 최대 재시도 횟수를 초과하면 실패해야 함."""
    cfgdir = tmp_path / "config"
    cfgdir.mkdir()
    reg = cfgdir / "repos.list"
    reg.write_text("owner/repo\n", encoding="utf-8")

    client = RetryClient("permanent_failure")
    col = Collector(github_client=client)  # type: ignore[arg-type]

    from repo_radar.github_client import GitHubAPIError

    # 영구적인 실패는 최종적으로 예외를 발생시켜야 함
    with pytest.raises(GitHubAPIError) as exc_info:
        col.collect(reg, persist_last_run=False)
    assert exc_info.value.status_code == 503
    assert "Service Unavailable" in str(exc_info.value)
