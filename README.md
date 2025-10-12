# repo-radar
Daily digest of your GitHub universe — PRs, issues, and reviews.

![License: WHATWANT Beerware](https://img.shields.io/badge/License-WHATWANT--Beerware-yellow?logo=beer&labelColor=black)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-46aef7?logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)

> Freedom, creativity, and a good drink 🍺

---

## 🚀 개발 시작하기

### Prerequisites
- [uv](https://docs.astral.sh/uv/) - Python 패키지 매니저
- Python 3.12+ (uv가 자동으로 관리)

### 설치 및 설정

```bash
# 1. 저장소 클론
git clone https://github.com/whawant-work/repo-radar.git
cd repo-radar

# 2. 의존성 설치 (Python 환경 자동 생성)
uv sync

# 3. 코드 품질 검사
uv run ruff check      # 린팅
uv run ruff format     # 포맷팅

# 4. 테스트 실행
uv run pytest

# 5. 애플리케이션 실행
uv run python main.py
```

### 개발 도구
- **린팅/포맷팅**: Ruff (Black + flake8 + isort 대체)
- **테스트**: pytest
- **의존성 관리**: uv (pip + virtualenv 대체)

---

## 🛠️ 기술 스택 제안

- **언어:** Python 3.12 이상
	- 표준 라이브러리 활용 극대화(HTTP, 일정, 파일 등)
- **API 연동:**
	- GitHub API: `requests` (필수 최소 외부 패키지)
- **템플릿 렌더링:**
	- Jinja2 (HTML Digest 생성, 대중적이고 유지보수 쉬움)
- **이메일 발송:**
	- 표준 `smtplib` (SMTP), 필요시 `email` 패키지
	- 대량/고급 전송은 SendGrid/SES 연동(선택, 외부 패키지 최소화)
- **스케줄링:**
	- GitHub Actions(권장) 또는 Linux cron(추가 설치 불필요)
- **데이터 저장:**
	- 파일(JSON/YAML) 또는 SQLite(표준 라이브러리 `sqlite3`)
- **테스트:**
	- `unittest` (표준), 필요시 `pytest`(선택)
- **로깅/모니터링:**
	- 표준 `logging` 모듈

**선정 기준:**
- Python 표준 라이브러리 우선, 필수 외부 패키지는 Jinja2, requests 정도로 최소화
- 대중적이고 문서/예제가 풍부한 기술
- GitHub Actions, cron 등 운영환경에 기본 내장된 스케줄러 활용
- 유지보수와 확장에 용이한 구조(레이어드/파이프라인/헥사고날 패턴 반영)

---

## 🧹 코딩 스타일 요약

이 저장소는 Ruff(포맷+린트)와 pre-commit 훅, GitHub Actions CI로 일관된 스타일을 유지합니다.

- 라인 길이 100, Python 3.12 타깃
- 네이밍은 PEP 8(pep8-naming) 준수: 클래스 PascalCase, 함수/변수 snake_case, 상수 UPPER_SNAKE_CASE
- 상세 규칙과 사용법: docs/style-guide.md 참고

---


## 🎯 MVP 범위 (v0.1)

### ✅ 포함사항
- **데이터 수집**: GitHub REST API를 통한 PR/Issue 수집
- **규칙 기반 분류**: 리뷰/답변/개발 카테고리 자동 분류
- **HTML Digest 생성**: 정적 HTML 페이지 생성 (템플릿 기반)
- **이메일 알림**: SMTP를 통한 요약 메일 발송
- **수동 실행**: CLI 기반 명령어 실행

### ❌ 제외사항 (후속 버전)
- 자동 스케줄러 (v0.2)
- GitHub Pages 자동 배포 (v0.2)
- GraphQL 최적화 (v0.3)
- 팀/조직 단위 대시보드 (v1.0)

### 🎪 완료 기준
- [ ] 최소 1개 공개 리포지토리에서 PR/Issue 수집 성공
- [ ] 리뷰/답변/개발 카테고리로 항목 분류 완료
- [ ] HTML Digest 파일 생성 확인
- [ ] 테스트 이메일 수신 확인
- [ ] 전체 파이프라인 E2E 테스트 통과

## Documentation

- [Requirements](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Coding style & naming](docs/style-guide.md)
- [Risks & Mitigations](docs/risks-and-mitigations.md)


## License

Licensed under the **WHATWANT BEERWARE LICENSE v1.0** 🍺
If you like this project, buy me a beer (or coffee) someday ☕

See the [LICENSE](./LICENSE) file for details.
