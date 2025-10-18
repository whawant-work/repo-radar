from __future__ import annotations

from datetime import UTC, datetime, timedelta

from repo_radar.digest import build_digest, build_sections, compute_kpis


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0, tzinfo=UTC).isoformat().replace("+00:00", "Z")


def test_compute_kpis_waiting_count_and_average_days() -> None:
    now = datetime.now(UTC)
    buckets = {
        "review": [
            # PR updated 2 days ago
            {
                "id": 1,
                "type": "PR",
                "updatedAt": _iso(now - timedelta(days=2)),
            },
            # Issue should be ignored for KPI
            {
                "id": 2,
                "type": "Issue",
                "updatedAt": _iso(now - timedelta(days=5)),
            },
            # PR updated 4 days ago
            {
                "id": 3,
                "type": "PR",
                "updatedAt": _iso(now - timedelta(days=4)),
            },
        ],
        "reply": [],
        "develop": [],
    }

    kpis = compute_kpis(buckets, now=now)
    # 2 PRs waiting in review bucket
    assert kpis["waiting_pr_count"] == 2
    # average of [2, 4] days => 3.0
    assert abs(kpis["avg_waiting_days"] - 3.0) < 1e-6


def test_build_sections_trims_and_keeps_priority_field() -> None:
    buckets = {
        "review": [
            {"id": 10, "type": "PR", "repo": "o/r", "number": 1, "title": "A", "priority": 99},
            {"id": 11, "type": "PR", "repo": "o/r", "number": 2, "title": "B", "priority": 50},
        ],
        "reply": [],
        "develop": [],
    }

    sections = build_sections(buckets, max_items_per_section=1)
    assert list(sections.keys()) == ["review", "reply", "develop"]
    assert len(sections["review"]) == 1
    assert sections["review"][0]["id"] == 10
    assert sections["review"][0]["priority"] == 99


def test_build_digest_schema_contains_kpis_and_sections() -> None:
    now = datetime.now(UTC)
    buckets = {
        "review": [
            {
                "id": 1,
                "type": "PR",
                "repo": "o/r",
                "number": 1,
                "title": "A",
                "priority": 10,
                "updatedAt": _iso(now - timedelta(days=1)),
            },
        ],
        "reply": [],
        "develop": [],
    }
    digest = build_digest(buckets, now=now, max_items_per_section=5)
    assert "generated_at" in digest
    assert "kpis" in digest and "sections" in digest
    assert digest["kpis"]["waiting_pr_count"] == 1
    assert isinstance(digest["kpis"]["avg_waiting_days"], float)
    assert "review" in digest["sections"]
