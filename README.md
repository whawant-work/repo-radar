# repo-radar

![License: WHATWANT Beerware](https://img.shields.io/badge/License-WHATWANT--Beerware-yellow?logo=beer&labelColor=black)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-46aef7?logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)

> Freedom, creativity, and a good drink 🍺

Daily digest of your GitHub universe — PRs, issues, and reviews that matter to you.

## 📖 소개

repo-radar는 GitHub에서 당신이 관심있는 저장소들의 활동을 모아서 매일 정리해주는 도구입니다.
PR, 이슈, 리뷰 등을 자동으로 수집하고 분류해서 HTML 다이제스트와 이메일로 전달합니다.

**주요 기능:**
- 🔍 GitHub 저장소 모니터링 (PR, 이슈, 리뷰)
- 📊 자동 분류 (리뷰 필요/답변 필요/개발 진행중)
- 📧 이메일 다이제스트 발송
- 🌐 HTML 리포트 생성
- ⚙️ 간편한 설정 관리

> 📋 상세한 기능 요구사항과 아키텍처는 [요구사항 문서](docs/requirements.md)와 [아키텍처 문서](docs/architecture.md)를 참고하세요.

---

## 🚀 빠른 시작

### 1. 설정하기
```bash
# .env 파일로 설정 (권장)
cp .env.sample .env
# 또는 환경변수로 직접 설정 (일부 설정)
export TIMEZONE=Asia/Seoul
export GITHUB_TOKEN=your_github_token
```

### 2. 실행하기
```bash
# 현재 설정 확인 및 저장소 목록 검증
uv run python main.py

# GitHub API 연결 확인 (토큰이 설정되어 있다면 private 저장소도 확인됩니다)
uv run python main.py --check-github octocat/Hello-World

# 다이제스트 생성 (향후 지원 예정)
# uv run python main.py --generate
```

### 3. 저장소 목록 파일로 관리하기 (권장)
`config/repos.list` 파일로 저장소 목록을 관리합니다. 저장소 목록은 환경변수 대신 파일로 관리합니다.

- 한 줄에 하나씩 `owner/repo` 형식으로 입력
- 빈 줄과 `#`로 시작하는 주석 줄은 무시
- 끝에 공백 후 `#`로 시작하는 인라인 주석 허용: `owner/repo  # 메모`

시작하려면 샘플을 복사하세요:

```bash
cp config/repos.sample.list config/repos.list
# 그런 다음 config/repos.list 파일을 편집하세요
```

프로그램 통합은 추후 CLI 서브커맨드로 제공될 예정입니다. 현재는 `repo_radar.registry` 모듈의 `load_repos`, `validate_repos` 함수와 GitHub REST 클라이언트(`repo_radar.github_client.GitHubClient`)를 직접 사용할 수 있습니다.

> 참고: `config/repos.list`는 개인 환경에 따라 달라지는 사용자 관리 파일이므로 git에 커밋되지 않도록 `.gitignore`에 포함되어 있습니다. 저장소에는 샘플(`config/repos.sample.list`)만 포함됩니다.

## ⚙️ 상세 설정

### 설정 우선순위
환경변수 > .env 파일 > 기본값

### 필수 설정

| 키 | 설명 | 예시 | 필수 여부 |
|---|---|---|:---:|
| `GITHUB_TOKEN` | GitHub Personal Access Token | `ghp_xxxxx` | ✅ |

### 선택 설정

| 키 | 설명 | 기본값 | 예시 |
|---|---|---|---|
| `TIMEZONE` | 시간대 | `UTC` | `Asia/Seoul` |
| `DAILY_AT` | 일일 실행 시각 (HH:MM) | `09:00` | `18:30` |
| `QUIET_HOURS` | 조용한 시간 (HH:MM-HH:MM) | - | `22:00-08:00` |
| `RULES_FILE` | 규칙 파일 경로 | - | `./config/rules.yaml` |
| `ME_LOGIN` | 규칙 엔진용 현재 사용자 로그인(선택) | - | `whatwant` |
| `EMAIL_PROVIDER` | 이메일 제공자 | `smtp` | `smtp\|ses\|sendgrid` |
| `EMAIL_SMTP_HOST` | SMTP 서버 호스트 | - | `smtp.gmail.com` |
| `EMAIL_SMTP_PORT` | SMTP 포트 | `587` | `465` |
| `EMAIL_SMTP_USER` | SMTP 사용자명 | - | `your-email@gmail.com` |
| `EMAIL_SMTP_PASS` | SMTP 비밀번호 | - | `your-app-password` |
| `EMAIL_FROM` | 발신자 이메일 | - | `noreply@example.com` |
| `EMAIL_TO` | 수신자 이메일 (쉼표구분) | - | `me@example.com,team@example.com` |
| `GH_PAGES_REPO` | GitHub Pages 저장소 | - | `owner/repo-radar-pages` |
| `GH_PAGES_BRANCH` | GitHub Pages 브랜치 | `gh-pages` | `main` |
| `BASE_URL` | 베이스 URL | - | `https://owner.github.io/repo-radar-pages` |

### .env 파일 예시
```dotenv
# 필수 설정
GITHUB_TOKEN=ghp_your_token_here

# 선택 설정
TIMEZONE=Asia/Seoul
DAILY_AT=09:00
QUIET_HOURS=22:00-08:00

# 이메일 설정 (SMTP)
EMAIL_PROVIDER=smtp
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=your-email@gmail.com
EMAIL_SMTP_PASS=your-app-password
EMAIL_FROM=noreply@example.com
EMAIL_TO=me@example.com,team@example.com

# GitHub Pages 설정 (향후 지원)
# GH_PAGES_REPO=owner/repo-radar-pages
# GH_PAGES_BRANCH=gh-pages
# BASE_URL=https://owner.github.io/repo-radar-pages

# 규칙 파일 (향후 지원)
# RULES_FILE=./config/rules.yaml
```

**⚠️ 주의사항**:
- GitHub 토큰은 `repo` 권한이 필요합니다
- `EMAIL_TO` 설정 시 `EMAIL_FROM`도 반드시 설정해야 합니다
- 저장소 목록은 `config/repos.list` 파일로 관리하세요 (`owner/name` 형식)

### 인증(PAT) 설정 가이드

repo-radar는 운영체제 환경변수와 `.env`를 모두 지원합니다. 우선순위는 환경변수 > .env > 기본값입니다.

1) 환경변수로 설정(zsh)
```zsh
export GITHUB_TOKEN=ghp_your_token_here
```

2) .env 파일 사용(권장)
- 루트의 `.env` 또는 `config/.env`를 자동 탐색하여 로드합니다.
- 샘플: `.env.sample` 파일을 복사하여 사용하세요.
```zsh
cp .env.sample .env
```

3) GitHub Actions/CI 시크릿 사용 팁
- GitHub Actions에서는 저장소 시크릿(예: `GH_PAT`)을 사용해 주입하세요.
- 예: `env: GITHUB_TOKEN: ${{ secrets.GH_PAT }}` 또는 GitHub가 제공하는 `secrets.GITHUB_TOKEN` 대신 퍼미션 조정이 가능한 PAT를 권장(필요 권한에 맞춰 최소 권한 부여).
- 토큰은 로그에서 자동 마스킹되며, 코드/Pages/로그에 노출되지 않도록 주의합니다.

> ⚙️ 전체 설정 옵션과 상세한 환경 변수 목록은 [요구사항 문서](docs/requirements.md#10-구성환경-변수예시)를 참고하세요.

---

## �️ 개발자 가이드

### 개발 환경 구축

**필요 조건:**
- [uv](https://docs.astral.sh/uv/) - Python 패키지 매니저
- Python 3.12+ (uv가 자동으로 관리)

```bash
# 1. 저장소 클론
git clone https://github.com/whawant-work/repo-radar.git
cd repo-radar

# 2. 개발 환경 설정
uv sync

# 3. 코드 품질 검사
uv run ruff check      # 린팅
uv run ruff format     # 포맷팅

# 4. 테스트 실행
uv run pytest
```

### 개발 가이드라인

repo-radar는 **Python 3.12+**를 기반으로 하며, 표준 라이브러리를 우선적으로 사용합니다.

- **코딩 스타일**: Ruff로 자동 관리 (line-length: 100)
- **네이밍**: PEP 8 준수 (클래스: PascalCase, 함수/변수: snake_case)
- **테스트**: pytest 사용, 최소 80% 커버리지 유지

> 🏗️ 상세한 기술 스택과 프로젝트 구조는 [아키텍처 문서](docs/architecture.md)를,
> ✍️ 코딩 스타일 세부 규칙은 [스타일 가이드](docs/style-guide.md)를 참고하세요.

## 📋 프로젝트 상태

### 현재 버전: v0.1 (MVP)

**✅ 완료된 기능:**
- 설정 관리 시스템 (환경변수/.env 파일 지원)
- 타입 안전 설정 검증 및 민감정보 마스킹
- GitHub REST API 클라이언트 (인증, 페이징, 재시도)
- 저장소 레지스트리 (파일 기반 관리)
- PR/Issue 수집기 (증분 수집, 상태 관리)
- 구조적 로깅 시스템 (민감정보 자동 마스킹)
- CLI 도구 (설정 확인, API 연결 테스트)
- 유닛 테스트 (33개, 100% 통과)

**🚧 향후 구현 예정:**
- 규칙 기반 분류 엔진 (리뷰/답변/개발)
- HTML 다이제스트 생성기
- SMTP 이메일 발송
- 스케줄러 (크론/GitHub Actions)
- GitHub Pages 자동 배포

> 📅 전체 로드맵과 마일스톤 계획은 [요구사항 문서](docs/requirements.md#14-마일스톤)를 참고하세요.

---

## 📚 문서

- [📋 요구사항](docs/requirements.md)
- [🏗️ 아키텍처](docs/architecture.md)
- [✍️ 코딩 스타일](docs/style-guide.md)
- [⚠️ 리스크 관리](docs/risks-and-mitigations.md)

## 🤝 기여하기

1. 이슈를 생성하거나 기존 이슈를 확인하세요
2. Fork 후 브랜치를 생성하세요: `git checkout -b feature/amazing-feature`
3. 변경사항을 커밋하세요: `git commit -m 'Add some amazing feature'`
4. 브랜치에 푸시하세요: `git push origin feature/amazing-feature`
5. Pull Request를 생성하세요

## 📄 라이센스

Licensed under the **WHATWANT BEERWARE LICENSE v1.0** 🍺
If you like this project, buy me a beer (or coffee) someday ☕

See the [LICENSE](./LICENSE) file for details.
