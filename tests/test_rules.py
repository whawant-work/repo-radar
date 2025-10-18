from __future__ import annotations

from datetime import UTC, datetime, timedelta

from repo_radar.rules import RuleConfig, RuleEngine


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0, tzinfo=UTC).isoformat().replace("+00:00", "Z")


def test_classify_review_by_requester_and_label() -> None:
    me = "alice"
    engine = RuleEngine(RuleConfig(me=me))
    now = datetime.now(UTC)
    item = {
        "id": 1,
        "type": "PR",
        "number": 10,
        "repo": "owner/repo",
        "title": "Refactor",
        "labels": ["Needs-Review"],
        "assignees": [],
        "author": "bob",
        "updatedAt": _iso(now - timedelta(hours=1)),
        "state": "open",
        "reviewRequests": [me],
    }
    cat, prio = engine.classify_item(item)
    assert cat == "review"
    # label(review)+recent(+5)+PR(+3) => >= 20+5+3 = 28
    assert prio >= 28


def test_classify_reply_when_assigned_and_question_label() -> None:
    me = "carol"
    engine = RuleEngine(RuleConfig(me=me))
    item = {
        "id": 2,
        "type": "Issue",
        "number": 11,
        "repo": "owner/repo",
        "title": "Need info",
        "labels": ["question"],
        "assignees": [me],
        "author": "dave",
        "updatedAt": _iso(datetime.now(UTC) - timedelta(days=2)),
        "state": "open",
        "reviewRequests": [],
    }
    cat, prio = engine.classify_item(item)
    assert cat == "reply"
    # reply label only => +10, no recent, no PR
    assert 10 <= prio < 20


def test_classify_develop_when_assigned_or_develop_label() -> None:
    me = "erin"
    engine = RuleEngine(RuleConfig(me=me))
    item = {
        "id": 3,
        "type": "PR",
        "number": 12,
        "repo": "owner/repo",
        "title": "Implement feature",
        "labels": ["enhancement"],
        "assignees": [me],
        "author": "frank",
        "updatedAt": _iso(datetime.now(UTC) - timedelta(hours=3)),
        "state": "open",
        "reviewRequests": [],
    }
    cat, prio = engine.classify_item(item)
    assert cat == "develop"
    # enhancement has no explicit bonus; recent + PR => >= 8
    assert prio >= 8


def test_bucket_sorting_by_priority_desc() -> None:
    engine = RuleEngine(RuleConfig(me="grace"))
    now = datetime.now(UTC)
    items = [
        # high priority (urgent + recent + PR)
        {
            "id": 100,
            "type": "PR",
            "number": 99,
            "repo": "o/r",
            "title": "Hotfix",
            "labels": ["urgent", "review"],
            "assignees": [],
            "author": "x",
            "updatedAt": _iso(now - timedelta(hours=1)),
            "state": "open",
            "reviewRequests": ["grace"],
        },
        # lower priority (question only, not recent)
        {
            "id": 101,
            "type": "Issue",
            "number": 100,
            "repo": "o/r",
            "title": "Please help",
            "labels": ["question"],
            "assignees": ["grace"],
            "author": "y",
            "updatedAt": _iso(now - timedelta(days=3)),
            "state": "open",
            "reviewRequests": [],
        },
    ]

    buckets = engine.classify(items)
    # ensure both items are classified
    assert sum(len(v) for v in buckets.values()) == 2
    # ensure sorting: the urgent review should come first in its bucket
    assert buckets["review"][0]["id"] == 100
