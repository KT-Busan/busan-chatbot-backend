# 🤖 부산 청년 챗봇 백엔드

부산시 청년들을 위한 **AI 기반 청년공간/프로그램 정보 제공** 챗봇의 백엔드 서버입니다.

> 프론트엔드(React+Vite)와 연동되어 대화, 공간/프로그램 탐색, 캐시/오버라이드 관리 등을 제공합니다.

---

## 💡 해결하려는 문제

부산에는 청년공간·프로그램이 **16개 구·군, 8개 카테고리**에 걸쳐 다양하게 존재하지만, 각 정보가 부산광역시, 각 구·군 청년센터, 개별 기관 홈페이지·SNS 등으로 **흩어져 있어** 청년이 자신에게 맞는 공간을 찾으려면 여러 사이트를 일일이 돌아다녀야 하는 정보 탐색 비용이 발생합니다. B-BOT은 이 흩어진 정보를 하나의 대화형 인터페이스로 모아, 지역·목적·인원 조건만으로 몇 초 안에 원하는 공간을 찾을 수 있도록 돕습니다.

## 🚀 향후 로드맵

* **카카오톡 채널 연동** : 별도 앱 설치 없이 카카오톡에서 바로 B-BOT을 사용할 수 있도록 채널 챗봇 연동
* **개인화 추천** : 사용자의 관심 키워드·이용 이력을 기반으로 맞춤 공간/프로그램 추천
* **공공데이터 API 정식 연동** : 현재의 크롤링 방식 대신 부산시·행정안전부 공공데이터포털 Open API로 전환하여 데이터 신뢰성과 갱신 주기 개선
* **소상공인/일자리 정보 확장** : 청년공간뿐 아니라 지역 소상공인 협업 공간, 청년 일자리·인턴 정보로 서비스 확장

---

## 🎯 프로젝트 개요

* **대화 처리** : OpenAI API(GPT-4o 계열)를 통해 자연어 질의에 응답
* **데이터 수집** : 크롤러를 통해 부산 지역 청년공간/프로그램 최신 정보 갱신
* **오버라이드 병합** : 수동으로 정제된 오버라이드 데이터를 원본과 자동 병합
* **조건 검색** : 지역/인원/목적 등 조건으로 빠르게 필터링
* **캐시 및 상태** : 파일 캐시/DB와 연동하여 응답 성능 최적화

---

## 🌟 주요 특징

* **AI 기반 대화** : OpenAI GPT-4o 활용
* **실시간 정보** : 주기/수동 크롤링으로 최신 정보 확보
* **Override 시스템** : 조정 데이터(override)와 원본 자동 병합
* **조건별 검색** : 지역, 인원, 목적 등 다중 필터
* **캐시 시스템** : 불필요한 외부 호출 최소화

---

## 📌 데이터 출처

청년공간/프로그램 정보는 [부산청년플랫폼(young.busan.go.kr)](https://young.busan.go.kr) 공개 페이지를 크롤링하여 수집하며, 저작권 및 출처는 부산광역시·부산청년플랫폼에 있습니다. 본 서비스는 정보 안내 목적으로만 데이터를 사용합니다.

---

## 🛠 기술 스택

* **Framework** : Flask (3.x)
* **Language/Runtime** : Python 3.12+
* **DB/ORM** : SQLite + SQLAlchemy
* **AI** : OpenAI (GPT-4o)
* **Crawler** : Requests, BeautifulSoup4
* **Env** : python-dotenv

### 🏗️ 인프라

* **Deploy** : Render (Web Service)
* **Storage** : Render Disk (Storage)

---

## 📁 프로젝트 구조

```text
busan-chatbot-backend/
├── .github/workflows/                 # CI/CD (선택)
├── config/                            # 설정/기본 데이터
│   ├── predefined_answers.py          # 미리 정의된 답변 템플릿
│   ├── youth_programs_cache.json      # 프로그램 캐시
│   ├── youth_spaces_cache.json        # 공간 캐시
│   ├── youth_spaces_overrides.json    # 공간 데이터 오버라이드
│   ├── spaces_busan_keyword.json      # 기본 청년공간 키워드(시드)
│   └── spaces_busan_youth.json        # 기본 청년공간 데이터(시드)
├── database/
│   └── models.py                      # SQLAlchemy 모델 정의(스키마)
├── handlers/                          # 비즈니스 로직 계층
│   ├── chat_handler.py                # 채팅/대화 처리 진입점
│   ├── program_handler.py             # 프로그램 조회/검색
│   ├── space_handler.py               # 공간 조회/검색/상세
│   └── user_handler.py                # 사용자/통계
├── instance/                          # 런타임 데이터(쓰기 가능 영역)
│   ├── chatbot.db                     # SQLite DB 파일
│   ├── youth_programs_cache.json      # 프로그램 캐시
│   ├── youth_spaces_cache.json        # 공간 캐시
│   └── youth_spaces_overrides.json    # 공간 데이터 오버라이드
├── services/                          # 외부 연동 계층
│   ├── youth_program_crawler.py       # 프로그램 크롤러
│   └── youth_space_crawler.py         # 공간 크롤러
├── app.py                             # Flask 앱 엔트리/라우팅 등록
├── requirements.txt                   # Python 의존성 목록
└── README.md                          # 프로젝트 문서(본 파일)
```
---

## ⚙️ 설치 및 실행

### 1) 클론 & 가상환경

```bash
git clone https://github.com/KT-Busan/busan-chatbot-backend.git
cd busan-chatbot-backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2) 의존성 설치

```bash
pip install -r requirements.txt
```

### 3) 환경 변수 설정

루트에 `.env` 파일을 생성합니다.

```env
OPENAI_API_KEY=YOUR_OPENAI_KEY
# 선택 항목
FLASK_ENV=production            # or development
PORT=8000                       # 개발 포트
# DB 경로를 커스텀하려면 (기본은 instance/chatbot.db)
DATABASE_URL=sqlite:///instance/chatbot.db
```

### 4) 로컬 실행

```bash
# 단일 파일 실행
python app.py
# 또는 (설정 시)
# flask --app app run --host 0.0.0.0 --port ${PORT:-8000}
```
---

## 🌐 API 문서 (요약)

| 카테고리            | 엔드포인트                                        | 메소드    | 설명               |
| --------------- | -------------------------------------------- | ------ | ---------------- |
| **채팅**          | `/api/chat`                                  | POST   | 채팅 메시지 전송        |
|                 | `/api/chat/{chat_id}`                        | DELETE | 채팅 삭제            |
|                 | `/api/history/{anonymous_id}`                | GET    | 채팅 히스토리 조회       |
| **사용자**         | `/api/user/{anonymous_id}`                   | GET    | 사용자 정보 조회        |
|                 | `/api/user`                                  | POST   | 사용자 생성           |
|                 | `/api/users/stats`                           | GET    | 사용자 통계           |
| **청년공간**        | `/api/spaces`                                | GET    | 전체 공간 목록         |
|                 | `/api/spaces/region/{region}`                | GET    | 지역별 공간 검색        |
|                 | `/api/spaces/search?keyword={keyword}`       | GET    | 키워드 검색           |
|                 | `/api/spaces/detail/{space_name}`            | GET    | 공간 상세 정보         |
|                 | `/api/spaces/all`                            | GET    | 전체 공간 목록(포맷)     |
|                 | `/api/spaces/busan-youth`                    | GET    | 부산 청년공간 데이터      |
|                 | `/api/spaces/crawl`                          | POST   | 수동 크롤링 실행        |
| **청년 프로그램**     | `/api/programs`                              | GET    | 전체 프로그램 목록       |
|                 | `/api/programs/region/{region}`              | GET    | 지역별 프로그램 검색      |
|                 | `/api/programs/search?keyword={keyword}`     | GET    | 키워드 검색           |
|                 | `/api/programs/crawl`                        | POST   | 수동 크롤링 실행        |
| **Override 관리** | `/api/spaces/overrides/status`               | GET    | Override 상태 확인   |
|                 | `/api/spaces/overrides/reload`               | POST   | Override 재로드     |
|                 | `/api/spaces/overrides/test/{region}`        | GET    | 지역별 Override 테스트 |
|                 | `/api/spaces/overrides/compare/{space_name}` | GET    | 공간 데이터 비교        |
| **디버깅**         | `/api/debug/spaces-status`                   | GET    | 공간 데이터 상태 요약     |
|                 | `/api/debug/reload-spaces`                   | POST   | 공간 데이터 강제 재로드    |
|                 | `/api/spaces/region/{region}/debug`          | GET    | 지역별 검색(디버그)      |
| **헬스체크**        | `/health`, `/api/health`                     | GET    | 서비스/세부 상태        |

### 요청 예시 (cURL)

```bash
# 채팅 전송
curl -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"anonymous_id": "abc-123", "message": "서면 근처 스터디 가능한 공간?"}'

# 지역별 공간 검색
curl http://localhost:8000/api/spaces/region/부산진구
```

---

## 🧩 운영 팁

* **캐시 갱신** : 급변경 시 `/api/debug/reload-spaces`로 강제 재로딩
* **오버라이드 정책** : `instance/youth_spaces_overrides.json`을 주원본과 병합(덮어쓰기 우선)
* **로그/모니터링** : Render 로그와 Flask 로거를 함께 사용
* **CORS** : 프런트엔드 도메인을 허용(필요 시 `flask-cors` 적용)

---

**🎉 부산 청년들의 더 나은 공간 활용을 위해!**
