"""
repo-radar Collector 모듈 (스켈레톤)
- 리포 루프 및 PR/Issue 수집 골격
- 페이로드 정규화 스키마
- 최근 활동 기간 파라미터 처리
"""
from typing import List, Dict, Any, Optional
from .github_client import GitHubClient
from .registry import load_repos

class Collector:
    def __init__(self, github_client: Optional[GitHubClient] = None):
        self.github_client = github_client or GitHubClient()

    def collect(self, repos_path, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        등록된 리포 목록을 순회하며 Open PR/Issue를 수집 (스켈레톤)
        since: ISO8601 형식의 최근 활동 기준 (예: '2025-10-10T00:00:00Z')
        Returns: 정규화된 페이로드 리스트
        """
        repos = load_repos(repos_path)
        items = []
        for repo in repos:
            owner, name = repo.split('/')
            # 실제 구현에서는 PR/Issue 리스트를 API로 받아야 함
            # 현재는 get_repo로 더미 데이터만 수집
            repo_info = self.github_client.get_repo(owner, name)
            items.append(self._normalize_item(repo_info, repo, "Repo"))
        return items

    def _normalize_item(self, raw: Dict[str, Any], repo: str, item_type: str) -> Dict[str, Any]:
        """
        API 응답을 내부 Item 스키마로 정규화
        """
        return {
            "id": raw.get("id"),
            "type": item_type,
            "number": raw.get("number"),
            "repo": repo,
            "title": raw.get("title"),
            "labels": raw.get("labels", []),
            "assignees": raw.get("assignees", []),
            "author": raw.get("user", {}).get("login"),
            "updatedAt": raw.get("updated_at"),
            "state": raw.get("state"),
            "reviewRequests": raw.get("requested_reviewers", []) if item_type == "PR" else [],
        }
