"""
Rules Engine (basic)

이 모듈은 수집된 GitHub 아이템(PR/Issue)을 다음 카테고리로 분류하고
간단한 우선순위 점수를 계산합니다.

- 카테고리: "review" | "reply" | "develop"
- 입력 아이템 스키마: repo_radar.collector.Collector._normalize_item 에서 생성된 dict
  필수 키: id, type(PR|Issue), number, repo, title, labels[], assignees[], author, updatedAt, state, reviewRequests[]

정책(기본값):
- review: 나(me)가 reviewRequests에 포함되었거나, 라벨이 review 관련 키워드
- reply: 나(me)가 assignee이고, 라벨이 질문/답변 대기 키워드
- develop: 나(me)가 assignee이거나, 개발/작업 성격 라벨

우선순위 계산(0~100):
- 라벨 가중치: urgent(+50) > high(+40) > bug(+30) > review(+20) > question(+10)
- 최근 업데이트 보정: 24시간 이내 +5
- PR 보정: type==PR이면 +3
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Iterable


Category = str  # "review" | "reply" | "develop"


def _lower_set(values: Iterable[str]) -> set[str]:
    return {v.strip().lower() for v in values if isinstance(v, str) and v.strip()}


@dataclass(frozen=True)
class RuleConfig:
    me: str | None = None  # 내 GitHub 로그인(선택)
    # 라벨 키워드(소문자 비교)
    review_labels: frozenset[str] = frozenset({"review", "needs-review", "rfr", "r4r"})
    reply_labels: frozenset[str] = frozenset({"question", "needs-reply", "needs-info", "awaiting-response"})
    develop_labels: frozenset[str] = frozenset({"todo", "backlog", "urgent", "bug", "enhancement", "feature"})


class RuleEngine:
    def __init__(self, config: RuleConfig | None = None):
        self.cfg = config or RuleConfig()

    # ---------- public API ----------
    def classify_item(self, item: dict[str, Any]) -> tuple[Category | None, int]:
        """단일 아이템을 분류하고 우선순위를 계산한다.

        Returns: (category | None, priority:int)
        """
        labels = _lower_set(item.get("labels", []))
        assignees = _lower_set(item.get("assignees", []))
        me = (self.cfg.me or "").strip().lower() or None

        # ----- 카테고리 판정 -----
        candidates: list[Category] = []

        # review: reviewRequests 포함 또는 라벨로 추론
        rr = _lower_set(item.get("reviewRequests", []))
        if (me and me in rr) or labels.intersection(self.cfg.review_labels):
            candidates.append("review")

        # reply: 내가 담당이며 질문/답변 대기 라벨
        if (me and me in assignees) and labels.intersection(self.cfg.reply_labels):
            candidates.append("reply")

        # develop: 내가 담당이거나 개발 성격 라벨
        if (me and me in assignees) or labels.intersection(self.cfg.develop_labels):
            candidates.append("develop")

        # 우선순위 카테고리 선호도: review > reply > develop
        category: Category | None
        if not candidates:
            category = None
        elif "review" in candidates:
            category = "review"
        elif "reply" in candidates:
            category = "reply"
        else:
            category = "develop"

        # ----- 우선순위 점수 -----
        priority = self._compute_priority(item, labels)
        return category, priority

    def classify(self, items: list[dict[str, Any]]) -> dict[Category, list[dict[str, Any]]]:
        """아이템 리스트를 카테고리별로 분류하고 priority 필드를 주입한다."""
        buckets: dict[Category, list[dict[str, Any]]] = {"review": [], "reply": [], "develop": []}
        for it in items:
            cat, prio = self.classify_item(it)
            if cat is None:
                continue
            enriched = dict(it)
            enriched["priority"] = prio
            buckets[cat].append(enriched)

        # 각 카테고리 내 우선순위 내림차순 정렬
        for k in buckets:
            buckets[k].sort(key=lambda x: x.get("priority", 0), reverse=True)
        return buckets

    # ---------- internals ----------
    def _compute_priority(self, item: dict[str, Any], labels: set[str]) -> int:
        score = 0

        # 라벨 가중치
        if "urgent" in labels:
            score += 50
        elif "high" in labels:
            score += 40
        elif "bug" in labels:
            score += 30
        elif labels.intersection(self.cfg.review_labels):
            score += 20
        elif labels.intersection(self.cfg.reply_labels):
            score += 10

        # 최근 업데이트 보정(24h)
        if _is_recent(item.get("updatedAt")):
            score += 5

        # PR 보정
        if (item.get("type") or "").upper() == "PR":
            score += 3

        # 경계 보정
        if score < 0:
            score = 0
        if score > 100:
            score = 100
        return score


def _parse_iso8601(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _is_recent(updated_at: str | None, *, within_hours: int = 24) -> bool:
    dt = _parse_iso8601(updated_at)
    if not dt:
        return False
    now = datetime.now(UTC)
    # datetime.fromisoformat may return aware/naive; ensure aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return now - dt <= timedelta(hours=within_hours)


__all__ = [
    "RuleConfig",
    "RuleEngine",
]
