# repo-radar
Daily digest of your GitHub universe — PRs, issues, and reviews.

![License: WHATWANT Beerware](https://img.shields.io/badge/License-WHATWANT--Beerware-yellow?logo=beer&labelColor=black)

> Freedom, creativity, and a good drink 🍺

---


## 🛠️ 기술 스택 제안

- **언어:** Python 3.10 이상  
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

## Documentation

- Requirements: see docs/requirements.md
- Architecture: see docs/architecture.md


## License

Licensed under the **WHATWANT BEERWARE LICENSE v1.0** 🍺  
If you like this project, buy me a beer (or coffee) someday ☕  

See the [LICENSE](./LICENSE) file for details.