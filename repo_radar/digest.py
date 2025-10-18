"""
Digest Builder

목표(WBS 5.1 Day3): KPI 계산(대기 PR 수/평균 대기일) 및 섹션 모델 구성.

입력: rules.RuleEngine.classify 의 결과 버킷
  {
    "review": [ {item... , priority:int}, ...],
    "reply":  [...],
    "develop": [...]
  }

출력: digest dict
  {
    "generated_at": ISO8601 UTC,
    "kpis": {
        "waiting_pr_count": int,
        "avg_waiting_days": float  # 소수 첫째 자리 반올림, PR이 없으면 0.0
    },
    "sections": {
        "review":  [ {id, type, repo, number, title, priority}, ...],
        "reply":   [...],
        "develop": [...]
    }
  }

가정/의사결정:
- "대기 PR"의 정의: Rules Engine 에 의해 review 카테고리로 분류된 PR 들.
- "평균 대기일": 각 PR 의 updatedAt 으로부터 현재 시각(UTC)까지의 경과일 수의 평균.
  - updatedAt 파싱 실패 시 해당 항목은 평균 계산에서 제외.
  - 유효한 샘플이 0개면 0.0 반환.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


CategoryBuckets = dict[str, list[dict[str, Any]]]


def _parse_iso8601(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _now_iso_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compute_kpis(buckets: CategoryBuckets, *, now: datetime | None = None) -> dict[str, Any]:
    """요약 KPI 계산.

    - waiting_pr_count: review 버킷의 PR 개수
    - avg_waiting_days: review 버킷의 PR 들에 대해 (now - updatedAt)의 일수 평균
    """
    now_dt = now or datetime.now(UTC)

    review_items = buckets.get("review", [])
    waiting_prs = [it for it in review_items if (it.get("type") or "").upper() == "PR"]
    waiting_pr_count = len(waiting_prs)

    deltas_days: list[float] = []
    for it in waiting_prs:
        dt = _parse_iso8601(it.get("updatedAt"))
        if dt is None:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        delta = now_dt - dt
        deltas_days.append(delta.total_seconds() / 86400.0)

    if deltas_days:
        avg_waiting_days = round(sum(deltas_days) / len(deltas_days), 1)
    else:
        avg_waiting_days = 0.0

    return {
        "waiting_pr_count": waiting_pr_count,
        "avg_waiting_days": avg_waiting_days,
    }


def build_sections(
    buckets: CategoryBuckets,
    *,
    max_items_per_section: int | None = None,
) -> CategoryBuckets:
    """섹션 모델 구성(카테고리별 리스트 정리).

    - 이미 rules.classify 가 priority 내림차순으로 정렬해주므로 유지
    - digest 에서는 주요 필드만 노출(간결화)
    - max_items_per_section 설정 시 상위 N개로 제한
    """
    def trim(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for it in items:
            out.append(
                {
                    "id": it.get("id"),
                    "type": it.get("type"),
                    "repo": it.get("repo"),
                    "number": it.get("number"),
                    "title": it.get("title"),
                    "priority": it.get("priority", 0),
                    # 내부 보존용 메타(렌더링 시 활용 가능)
                    "updatedAt": it.get("updatedAt"),
                    "labels": it.get("labels", []),
                }
            )
        if isinstance(max_items_per_section, int) and max_items_per_section >= 0:
            return out[:max_items_per_section]
        return out

    return {
        "review": trim(buckets.get("review", [])),
        "reply": trim(buckets.get("reply", [])),
        "develop": trim(buckets.get("develop", [])),
    }


def build_digest(
    buckets: CategoryBuckets,
    *,
    now: datetime | None = None,
    max_items_per_section: int | None = None,
) -> dict[str, Any]:
    """Digest 전체 모델 생성.

    반환 스키마는 모듈 상단의 출력 예시 참고.
    """
    kpis = compute_kpis(buckets, now=now)
    sections = build_sections(buckets, max_items_per_section=max_items_per_section)
    return {
        "generated_at": _now_iso_utc(),
        "kpis": kpis,
        "sections": sections,
    }


__all__ = [
    "compute_kpis",
    "build_sections",
    "build_digest",
]
