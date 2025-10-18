"""
repo-radar Collector 모듈
- 리포 루프 및 PR/Issue 수집
- 페이로드 정규화 스키마
- updatedAt 기반 증분 수집(최소)
"""
from datetime import datetime
from typing import Any

from .github_client import GitHubClient
from .registry import load_repos
from .state import get_last_run, set_last_run


class Collector:
    def __init__(self, github_client: GitHubClient | None = None):
        self.github_client = github_client or GitHubClient()

    def collect(
        self,
        repos_path,
        since: str | None = None,
        *,
        persist_last_run: bool = True,
    ) -> list[dict[str, Any]]:
        """
        등록된 리포 목록을 순회하며 Open PR/Issue를 수집.

        - 증분 수집: 입력 since 또는 저장된 last_run 기준으로 필터링.
        - Issues API 사용: PR/Issue 동시 수집(state=open, per_page=100, since=ISO8601).
        - 완료 후 persist_last_run=True면 현재 시각으로 last_run 갱신.

        since: ISO8601 형식의 기준(예: '2025-10-10T00:00:00Z')
        Returns: 정규화된 페이로드 리스트
        """
        repos = load_repos(repos_path)
        items: list[dict[str, Any]] = []

        # Determine baseline timestamp for incremental collection
        baseline = since or get_last_run()

        for repo in repos:
            owner, name = repo.split("/")
            # Use Issues API to fetch PRs + Issues updated since baseline
            params: dict[str, Any] = {"state": "open", "per_page": 100}
            if baseline:
                params["since"] = baseline
            path = f"/repos/{owner}/{name}/issues"
            for raw in self.github_client.iter_json_list(path, params=params):
                # The issues API returns both issues and PRs; PRs contain a 'pull_request' key
                item_type = "PR" if isinstance(raw, dict) and raw.get("pull_request") else "Issue"
                norm = self._normalize_item(raw, f"{owner}/{name}", item_type)
                # Post-filter by updatedAt baseline to ensure strictness (updated_at > last_run)
                if baseline and norm.get("updatedAt"):
                    try:
                        if not self._is_updated_after(norm["updatedAt"], baseline):
                            continue
                    except Exception:
                        # If parsing fails, include item to avoid missing updates
                        pass
                items.append(norm)

        # Persist new last_run timestamp at the end of collection
        if persist_last_run:
            set_last_run()  # current UTC now

        return items

    def _normalize_item(self, raw: dict[str, Any], repo: str, item_type: str) -> dict[str, Any]:
        """
        API 응답을 내부 Item 스키마로 정규화
        """
        # labels/assignees는 객체 배열일 수 있어 name/login만 추출 시도
        labels = []
        if isinstance(raw.get("labels"), list):
            for lb in raw["labels"]:
                if isinstance(lb, dict) and "name" in lb:
                    labels.append(lb["name"])
                else:
                    labels.append(lb)
        assignees = []
        if isinstance(raw.get("assignees"), list):
            for a in raw["assignees"]:
                if isinstance(a, dict) and "login" in a:
                    assignees.append(a["login"])
                else:
                    assignees.append(a)
        review_requests = []
        if item_type == "PR":
            reqs = raw.get("requested_reviewers")
            if isinstance(reqs, list):
                for r in reqs:
                    if isinstance(r, dict) and "login" in r:
                        review_requests.append(r["login"])

        return {
            "id": raw.get("id"),
            "type": item_type,
            "number": raw.get("number"),
            "repo": repo,
            "title": raw.get("title"),
            "labels": labels,
            "assignees": assignees,
            "author": (raw.get("user", {}) or {}).get("login"),
            "updatedAt": raw.get("updated_at"),
            "state": raw.get("state"),
            "reviewRequests": review_requests,
        }

    @staticmethod
    def _is_updated_after(updated_at_iso: str, baseline_iso: str) -> bool:
        """Return True if updated_at_iso is strictly after baseline_iso."""
        # RFC3339 like '2025-10-12T05:00:00Z' or with timezone offset
        def parse(s: str) -> datetime:
            s = s.replace("Z", "+00:00")
            return datetime.fromisoformat(s)
        return parse(updated_at_iso) > parse(baseline_iso)
