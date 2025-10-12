# 코딩 스타일 & 네이밍 가이드

문서 버전: 0.1
마지막 업데이트: 2025-10-12

본 문서는 repo-radar의 일관된 코드 품질을 위해 포맷팅, 린팅, 네이밍 규칙과 실행 방법을 정의합니다. 모든 설정은 `pyproject.toml`의 `[tool.ruff]`에 반영되어 있으며, pre-commit과 CI에서 자동 검증됩니다.

## 1) 도구 스택
- Ruff Formatter: Black 스타일과 호환, 기본 이중따옴표
- Ruff Linter: 규칙 세트 활성화
  - E/W (pycodestyle), F (pyflakes), I (isort), B (bugbear), UP (pyupgrade), N (pep8-naming), A (builtins)
- 타깃 버전: Python 3.12
- 라인 길이: 100

## 2) 네이밍 규칙 (pep8-naming 요약)
- 클래스: PascalCase
  - 예) `RepoRegistry`, `DigestBuilder`
- 함수/메서드/변수: snake_case
  - 예) `load_config()`, `build_digest()`, `repo_list`
- 상수: UPPER_SNAKE_CASE
  - 예) `DEFAULT_TIMEOUT`, `MAX_RETRIES`
- 비공개 멤버: 선행 언더스코어 권장
  - 예) `_cache`, `_load_env()`
- 약어/이니셜리즘: 필요 시 소문자 기준으로 단어화
  - 예) `github_token` (GHToken 등은 지양)

## 3) 임포트 & 정리(isort by Ruff)
- 표준 라이브러리 → 서드파티 → 퍼스트파티(`repo_radar`) 순서
- `from x import y as z` 합치기 허용(combine-as-imports)

## 4) 스타일 세부 규칙
- 따옴표: 기본 "double" (Ruff formatter 설정)
- 들여쓰기: 4 spaces
- 줄바꿈: 운영체제 기본(line-ending auto)
- 복잡도: mccabe max-complexity = 10 (함수 단순화 권장)
-
- 파일별 예외: `__init__.py`는 편의상 `F401, F403` 무시(공개 API 수출 패턴)

## 5) 흔한 린트 위반과 처리
- 미사용 임포트/변수(F401/F841): 제거 또는 `_` 프리픽스 사용
- mutable 기본 인자: 사용 금지, `None` + 내부 초기화 패턴 사용
- 예외 처리: 맥락 있는 메시지/로깅 포함, 맹목적 bare `except:` 금지
- 길어진 라인: 100자 초과 시 적절한 줄바꿈 사용

## 6) 실행 방법

uv 사용 시:
```zsh
# 1) 도구 설치(1회)
uv tool install ruff>=0.8.0

# 2) 전체 코드 점검
ruff check .

# 3) 자동 수정(가능한 항목만)
ruff check --fix .

# 4) 포맷 적용
ruff format .
```

pip 사용 시:
```zsh
python -m pip install --upgrade pip
pip install ruff>=0.8.0
ruff check .
ruff check --fix .
ruff format .
```

## 7) VS Code 연동
- 확장: `Ruff`(charliermarsh.ruff) 설치 권장
- `.vscode/settings.json` 예시

```jsonc
{
  "editor.formatOnSave": true,
  "python.analysis.typeCheckingMode": "basic",
  "files.trimTrailingWhitespace": true,
  "files.insertFinalNewline": true,

  // Ruff VS Code extension settings
  "ruff.enable": true,
  "ruff.lint.run": "onSave",
  "ruff.organizeImports": true,
  "ruff.format.enable": true,

  // Python extension 포맷터 중복 방지
  "python.formatting.provider": "none"
}
```

## 8) pre-commit 훅
```zsh
pip install pre-commit
pre-commit install
# 이후 git commit 시 ruff lint/format이 자동 실행됩니다.
```
- 훅 정의 파일: `.pre-commit-config.yaml`

## 9) CI (GitHub Actions)
- 워크플로우: `.github/workflows/ci.yml`
- 항목: `ruff check` + `ruff format --check`

---

## 📚 관련 문서
- [📋 요구사항 명세서](./requirements.md) - 프로젝트 전체 요구사항
- [🏗️ 아키텍처 설계](./architecture.md) - 시스템 구조와 설계 원칙
- [⚠️ 리스크 관리](./risks-and-mitigations.md) - 개발/운영 리스크 및 대응

---
*의견/변경 제안은 PR로 환영합니다.* 🧭
