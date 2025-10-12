from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from repo_radar.registry import RepoRegistryError, load_repos, validate_repos


def write(tmp: Path, content: str) -> Path:
    p = tmp / "repos.list"
    p.write_text(content, encoding="utf-8")
    return p


def test_load_repos_basic_parsing(tmp_path: Path) -> None:
    f = write(
        tmp_path,
        """
        # sample
        whatwant/repo-radar
        octocat/Hello-World

        # inline comment allowed
        myorg/private#note: missing space before '#'
        other/repo  # trailing comment ok
        whatwant/repo-radar  # duplicate should be removed
        """,
    )

    # The line 'myorg/private # note...' should be invalid because '#' isn't preceded by space
    with pytest.raises(RepoRegistryError):
        load_repos(f)


def test_load_repos_with_inline_comment_and_duplicates(tmp_path: Path) -> None:
    f = write(
        tmp_path,
        """
        # valid with trailing comment
        other/repo  # trailing comment ok
        whatwant/repo-radar
        other/repo  # duplicate
        """,
    )
    repos = load_repos(f)
    assert repos == ["other/repo", "whatwant/repo-radar"]


def test_load_repos_invalid_line_reports_number(tmp_path: Path) -> None:
    f = write(
        tmp_path,
        """
        ok/one
        badformat
        ok/two
        """,
    )
    with pytest.raises(RepoRegistryError) as ei:
        load_repos(f)
    assert "line 3" in str(ei.value) or "line 2" in str(ei.value)  # depending on leading newline


class DummyResp:
    def __init__(self, status_code: int, json_data: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._json = json_data or {}

    def json(self) -> dict[str, Any]:
        return self._json


def test_validate_repos_maps_status_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_get(url: str, headers: dict[str, str], timeout: int) -> DummyResp:  # type: ignore[override]
        calls.append(url)
        if url.endswith("/ok/repo"):
            return DummyResp(200)
        if url.endswith("/missing/repo"):
            return DummyResp(404)
        if url.endswith("/private/repo"):
            return DummyResp(403)
        return DummyResp(500)

    import repo_radar.registry as reg

    monkeypatch.setattr(reg.requests, "get", fake_get)

    repos = ["ok/repo", "missing/repo", "private/repo", "weird/repo"]
    errors = validate_repos(repos, github_token=None)

    assert errors == {
        "missing/repo": "not found",
        "private/repo": "unauthorized or forbidden",
        "weird/repo": "http 500",
    }
    assert any("ok/repo" in c for c in calls)
