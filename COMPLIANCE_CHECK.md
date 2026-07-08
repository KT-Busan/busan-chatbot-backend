# 컴플라이언스 점검 결과 (busan-chatbot-backend)

> K-AI Contents Award Track B(솔루션 부문) 출품 전 진행한 보안/규정 점검 기록. 점검일: 2026-07-08.

## 1. 민감정보 노출 점검

- 현재 코드 트리 및 `git log --all -p`(전체 커밋 히스토리) 전수 검색 결과, OpenAI API 키(`sk-...`), AWS 키(`AKIA...`) 등 하드코딩된 민감정보 **없음**.
- `.env` 파일 및 SQLite DB 파일(`*.db`)이 과거에도 커밋된 이력 **없음** — 저장소에는 `.env.example`만 존재하며 실제 키 값은 포함하지 않음.
- `OPENAI_API_KEY`는 `os.getenv("OPENAI_API_KEY")`(`handlers/chat_handler.py`)로만 참조되며, 코드에 직접 노출되지 않음.

## 2. `.gitignore` 점검

- `.env`, `instance/`(SQLite DB 및 런타임 캐시가 저장되는 디렉토리), `venv/`, `__pycache__/` 등이 모두 `.gitignore`에 포함되어 있음을 확인. 추가 조치 불필요.

## 3. 개인정보 최소 수집 원칙

- `database/models.py`의 `User` 모델은 `anonymous_id`(클라이언트에서 생성한 UUID 기반 익명 식별자)만 저장하며, 이름·전화번호·이메일 등 **실명 개인정보 컬럼은 존재하지 않음**.
- `Chat`, `Message` 모델도 대화 내용/제목/타임스탬프만 저장하고 사용자를 특정할 수 있는 필드는 없음.
- → 개인정보 무단 수집 소지 없음.

## 4. CORS 설정

- `app.py`의 `ALLOWED_ORIGINS`는 환경변수로 오버라이드 가능한 화이트리스트 방식이며, 기본값도 `https://kt-busan.github.io`, Render 프로덕션 도메인, 로컬 개발 포트로 한정됨. `Access-Control-Allow-Origin: *` 와일드카드 사용 **없음**.

## 5. 의존성 취약점 점검 (pip-audit)

- `pip-audit -r requirements.txt` 실행 결과 Flask, requests, urllib3, idna, lxml, python-dotenv, werkzeug에서 총 13건의 알려진 CVE 발견 → 아래와 같이 패치 버전으로 업데이트 완료, 재점검 시 **"No known vulnerabilities found"** 확인.

| 패키지 | 변경 전 | 변경 후 |
|---|---|---|
| Flask | 3.1.1 | 3.1.3 |
| requests | 2.32.4 | 2.33.0 |
| urllib3 | 2.5.0 | 2.7.0 |
| idna | 3.10 | 3.15 |
| lxml | 5.3.0 | 6.1.0 |
| python-dotenv | 1.1.1 | 1.2.2 |
| werkzeug | 3.1.3 | 3.1.6 |

- 업데이트 후 로컬에서 `python app.py` 정상 기동 및 `/health` 200 응답 확인.

## 6. 크롤링 데이터 출처 표기

- `services/youth_space_crawler.py`, `services/youth_program_crawler.py` 상단에 데이터 출처(부산청년플랫폼, `young.busan.go.kr`) 주석 명시.
- README 및 지원서 상 "청년공간/프로그램 정보는 부산청년플랫폼 공개 페이지를 크롤링하여 수집" 문구로 출처를 밝힐 것(README 업데이트 시 반영).

## 7. CI/CD 정리

- 실제 배포는 Render(README/CORS 기본 도메인 기준)이나, `fly.toml` 설정 없이 Fly.io 배포를 시도하는 `.github/workflows/fly-deploy.yml`이 남아 있어 main 브랜치에 push할 때마다 실패했을 가능성이 높음 → **삭제**하여 불필요한 CI 실패 기록을 제거함.

## 8. 남은 확인 필요 사항 (사용자 확인 필요)

- Render 대시보드에서 `OPENAI_API_KEY`, `ALLOWED_ORIGINS` 등 환경변수가 실제로 설정되어 있는지 재확인 권장(코드상으로는 노출 없으나, 배포 환경변수 자체는 이 점검 범위 밖).
- 과거 GitHub Actions 로그(Fly.io 워크플로우 실행 기록)에 민감정보가 남아있지 않은지 GitHub Actions 탭에서 별도 확인 권장.
