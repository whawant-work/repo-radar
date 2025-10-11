# repo-radar 요구사항 명세서

문서 버전: 0.1 (초안)  
마지막 업데이트: 2025-10-12  
작성자: 유지보수자

## 1. 개요
- 목적: 여러 GitHub 리포지토리를 등록해 두면, 하루 1회 PR/Issue 현황을 수집·분석하여
  - 내가 지금 리뷰해야 할 것
  - 내가 답변해야 할 것
  - 내가 개발(작업)해야 할 것
  을 요약한 Digest를 생성하고, GitHub Pages로 게시하며 이메일로 알림을 보낸다.

## 2. 범위
- In scope
  - 리포지토리 등록/관리
  - GitHub API 기반 데이터 수집(REST v3 및/또는 GraphQL v4)
  - 규칙 기반 분류(리뷰/답변/개발)
  - 일일 스케줄 실행(크론/워크플로우/서버 잡)
  - 정적 Digest 페이지 생성 및 gh-pages 배포
  - 이메일로 Digest 알림 발송
  - 기본 설정/환경 변수 관리, 로그/모니터링(기본)
- Out of scope(초기 버전)
  - 모바일 앱, 실시간 푸시 알림
  - 조직 단위 권한 위임/팀별 대시보드(확장 항목)
  - 고급 ML 추천/랭킹

## 3. 이해관계자 및 페르소나
- 개인 개발자: 본인에게 배정된 이슈/PR, 멘션된 스레드, 리뷰 요청을 빠르게 소화
- 팀 리드: 팀 리포지토리 전반의 리뷰 적체, 긴급 이슈 파악
- Ops/관리자: 토큰·설정 관리, 스케줄 신뢰성 보장

## 4. 용어
- Item: Issue 또는 Pull Request
- Digest: 하루 단위로 생성되는 요약 산출물(HTML/JSON)
- Rule: Item을 카테고리(리뷰/답변/개발)로 분류하는 조건 집합

## 5. 기능 요구사항
5.1 리포지토리 등록/관리
- 사용자는 GitHub 리포지토리(개인/조직, 공개/비공개)를 등록/삭제/나열할 수 있어야 한다.
- 비공개 접근 시 최소 권한의 GitHub 토큰 사용(Repo: read).

5.2 인증/권한
- GitHub Personal Access Token(PAT) 또는 GitHub App 자격 증명 지원.
- 토큰은 암호화 저장(파일/DB 시 at-rest 암호화) 및 최소 권한 원칙 준수.

5.3 스케줄 실행
- 기본: 하루 1회 지정 시각(사용자 시간대) 실행.
- 실패 시 재시도(백오프), 최대 N회 후 실패 기록.
- 수동 실행 트리거 가능(CLI/Action dispatch).

5.4 데이터 수집
- 항목: Open PR, Open Issue, 최근 7~14일 활동(코멘트/리뷰/멘션).
- Rate limit 관리(잔여 한도 체크, 요청 배치, ETag/If-None-Match 캐시).
- 중복/변경 감지(UpdatedAt 기반 증분 수집).

5.5 규칙 기반 분류
- 리뷰해야 할 것:
  - Review requests에 사용자/팀이 포함
  - 사용자가 코멘트/리뷰 남겼고 업데이트가 발생(추가 커밋/멘션)하여 재확인 필요
- 답변해야 할 것:
  - 자신이 멘션된 코멘트/이슈/PR에 미답변 상태
  - 자신이 마지막으로 질문받고 일정 시간 응답 없음
- 개발해야 할 것:
  - Assignee가 본인
  - “todo”, “backlog”, “urgent” 등 라벨 규칙 일치
  - 마감일(due) 임박
- 각 규칙은 설정 파일로 커스터마이즈 가능(라벨 키워드, 데드라인 임계값, snooze).

5.6 Digest 생성
- 출력: 정적 HTML(필수), JSON(선택).
- 섹션: 요약 KPIs(대기 PR 수/평균 대기일), 리뷰/답변/개발 목록, 변경 이력 링크.
- 각 항목에 링크, 라벨, 작성자, 업데이트 시각, 우선순위 표시.
- 템플릿 기반 렌더링(예: Nunjucks/Handlebars/EJS).

5.7 GitHub Pages 게시
- gh-pages 브랜치로 정적 산출물 커밋/푸시.
- 커스텀 베이스 URL, 인덱스 페이지, 일자별 아카이브(/yyyy-mm-dd/index.html).

5.8 이메일 알림
- 요약 본문(Top N) + 전체 Digest 링크.
- 수신자: 개인 메일 혹은 메일링 리스트.
- 전송 채널: SMTP 또는 SendGrid/SES 중 하나 선택 가능.
- Quiet hours/주말 스킵 옵션.

5.9 설정 관리
- 환경 변수와 설정 파일(config.yaml/json) 병행 지원.
- 주요 키: TIMEZONE, DAILY_AT, REPOS[], RULES, EMAIL_SMTP_*, EMAIL_TO[], GH_PAGES_REPO/BRANCH, BASE_URL, GITHUB_TOKEN.

5.10 관측성
- 실행 로그(레벨: info/warn/error), 메트릭(수집 시간, 항목 수, 실패율).
- 실패 시 알림(이메일 제목 접두사 [FAIL]).

## 6. 비기능 요구사항
- 성능: 리포지토리 50개, 최근 활동 5천 항목 기준 5분 내 수집·분류·렌더링.
- 신뢰성: 작업 실패율 < 1%/일, 재시도 후 최종 성공률 ≥ 99.9%.
- 보안: 비밀값은 환경 변수/비밀 저장소에만; 전송 시 TLS; 최소 권한 토큰.
- 프라이버시: 이메일 수신자/히스토리 보호, 공개 Pages에 민감 정보 노출 금지(비공개 리포지는 링크/메타만 표시 옵션 제공).
- 국제화: 초기 한국어, 영어 확장 가능(템플릿 번역 키).
- 접근성: 기본 a11y 준수(대비, 스크린리더 친화적 마크업).
- 호환성: Linux 환경, GitHub.com 우선(Enterprise는 후속).

## 7. 외부 연동 및 제약
- GitHub API: REST v3 + GraphQL v4 혼용(리뷰 요청/멘션 탐색에 GraphQL 권장).
- 이메일: SMTP(STARTTLS) 또는 SendGrid/SES API.
- GitHub Pages: gh-pages 브랜치, Actions로 자동 배포 옵션.

## 8. 데이터 모델(초안)
- Repository{id, owner, name, private, defaultBranch}
- User{id, login, email, teams[]}
- Item{id, type(PR|Issue), number, repoId, title, labels[], assignees[], author, updatedAt, state, reviewRequests[]}
- Rule{id, name, type, conditions, priority}
- Digest{id, date, itemsByCategory{review[], reply[], build[]}, kpis, path}
- SyncJob{id, startedAt, finishedAt, status, stats, error?}

## 9. 워크플로우(개략)
1) 스케줄 트리거 → 2) 리포지토리별 증분 수집 → 3) 규칙 적용/분류/우선순위 → 4) Digest 렌더링(HTML/JSON) → 5) gh-pages 커밋/푸시 → 6) 이메일 발송 → 7) 메트릭/로그 기록

## 10. 구성/환경 변수(예시)
- GITHUB_TOKEN
- TIMEZONE=Asia/Seoul
- DAILY_AT=09:00
- REPOS=owner1/repoA,owner2/repoB
- GH_PAGES_REPO=you/repo-radar-pages
- GH_PAGES_BRANCH=gh-pages
- BASE_URL=https://you.github.io/repo-radar-pages
- EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_SMTP_USER, EMAIL_SMTP_PASS, EMAIL_FROM, EMAIL_TO
- RULES_FILE=./config/rules.yaml

## 11. 수용 기준(샘플)
- 리포지토리 등록
  - Given 유효한 토큰과 repo 주소 When 등록 명령 실행 Then 목록에 추가되고 다음 수집 시 반영된다.
- 분류 규칙
  - Given 리뷰 요청된 PR When 일일 실행 Then “리뷰해야 할 것” 섹션에 PR이 포함된다.
- Digest 생성/게시
  - Given 전일 대비 변경 사항 존재 When 실행 완료 Then gh-pages에 yyyy-mm-dd 인덱스가 생성되고 브라우저에서 열람 가능하다.
- 이메일
  - Given EMAIL_TO 설정 When 실행 완료 Then 수신자는 Top N 항목과 링크가 포함된 메일을 1건 수신한다.
- 실패 처리
  - Given GitHub API 502 When 재시도 정책 적용 Then 최대 3회 재시도 후 실패 시 [FAIL] 제목의 실패 알림을 보낸다.

## 12. 테스트 전략
- 유닛: 규칙 매칭, 렌더 템플릿, 타임존 스케줄 계산.
- 통합: GitHub API 모킹(vcr/fixtures), SMTP 모킹.
- E2E: 샘플 공개 리포지토리로 실제 실행하여 gh-pages/메일 확인.
- 부하: 대량 리포/항목 시나리오로 성능 확인.

## 13. 배포/운영
- 옵션 A: GitHub Actions(크론 스케줄 + Pages 배포 + 메일 시크릿)
- 옵션 B: 자체 서버/컨테이너(cron + 시스템 서비스)
- 로그 보존, 시크릿 교체 주기, 토큰 만료 모니터링.

## 14. 마일스톤
- v0.1(MVP): REST 수집, 기본 규칙, HTML Digest, SMTP 메일, 수동 실행
- v0.2: 스케줄러, gh-pages 자동 배포, 증분 수집
- v0.3: GraphQL 최적화, 규칙 파일 커스터마이즈, 메트릭
- v1.0: 팀/조직 지원, UI 설정 페이지, 다국어

## 15. 리스크/대응
- API Rate limit 초과 → 캐시/증분/GraphQL, 백오프
- 민감 정보 노출 → 비공개 항목 마스킹/옵트아웃
- 이메일 스팸 → 빈도/Quiet hours/요약 Only

## 16. 오픈 이슈(결정 사항)
- GitHub App vs PAT 중 어떤 인증 방식 우선?
- Digest 공개 범위: 전부 공개 vs 민감 항목 마스킹?
- 이메일 프로바이더 선택(SMTP/SES/SendGrid)?
- 팀/조직 단위 초기 지원 여부?