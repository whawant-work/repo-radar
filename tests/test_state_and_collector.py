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


def test_collector_persists_last_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
