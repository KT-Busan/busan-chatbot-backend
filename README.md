# 🤖 Busan Youth Chatbot - Backend

부산시 청년들을 위한 **청년공간 및 프로그램 정보 제공 챗봇**의 백엔드 서버입니다.
이 서버는 사용자의 질문을 받아 OpenAI의 대규모 언어 모델(LLM)과 상호작용하고,
실시간 크롤링을 통한 최신 정보 제공 및 대화 내용을 데이터베이스에 저장·관리하는 역할을 합니다.

---

## ✨ 주요 기능(Features)

### 🧠 **지능형 챗봇 시스템**

- **OpenAI GPT-4o 연동**: 자연스럽고 정확한 대화형 AI 응답
- **페르소나 기반 응답**: 부산 청년공간 전문가 'B-BOT' 페르소나로 일관된 답변 제공
- **컨텍스트 인식**: 이전 대화 맥락을 기반으로 한 연속적인 대화 지원

### 🏢 **부산 청년공간 정보 서비스**

- **실시간 공간 정보**: 부산시 전 지역 청년공간 정보 자동 크롤링 및 제공
- **지역별 검색**: 16개 구·군별 청년공간 필터링 검색
- **키워드 검색**: 시설명, 용도, 특징별 맞춤 검색 기능
- **상세 정보 제공**: 위치, 연락처, 이용시간, 홈페이지 등 종합 정보

### 📋 **청년 프로그램 관리**

- **모집중 프로그램**: 현재 모집중인 청년 프로그램만 실시간 수집
- **마감일 관리**: 프로그램 마감일 임박 순 자동 정렬
- **지역별 프로그램**: 지역 맞춤 프로그램 정보 제공
- **자동 크롤링**: 정기적 데이터 업데이트로 최신 정보 보장

### 💬 **대화 관리 시스템**

- **사용자별 히스토리**: 익명 ID 기반 개별 대화 기록 관리
- **세션 관리**: 다중 채팅 세션 지원 및 관리
- **영구 저장**: SQLite 기반 안정적인 대화 데이터 보존

### ⚡ **사전 정의 답변**

- **즉시 응답**: 자주 묻는 질문에 대한 API 호출 없는 빠른 답변
- **카테고리별 안내**: 체계적인 메뉴 기반 정보 탐색 지원

---

## 🛠 기술 스택(Tech Stack)

### **Backend Framework**

- **Python 3.11+**: 메인 개발 언어
- **Flask**: 경량 웹 프레임워크
- **Modular Architecture**: 기능별 핸들러 분리 구조

### **Database & ORM**

- **SQLite**: 임베디드 데이터베이스
- **Flask-SQLAlchemy**: Python ORM

### **External APIs & Services**

- **OpenAI API**: GPT-4o 모델 연동
- **Web Scraping**: BeautifulSoup4 + requests 기반 크롤링

### **Key Libraries**

```
Flask==3.1.1                    # 웹 프레임워크
Flask-SQLAlchemy==3.1.1         # ORM
openai==1.97.0                  # OpenAI API 클라이언트
beautifulsoup4==4.12.2          # 웹 크롤링
requests==2.32.4               # HTTP 클라이언트
python-dotenv==1.1.1           # 환경 변수 관리
flask-cors==6.0.1               # CORS 처리
```

---

## 🚀 시작하기(Getting Started)

### 📋 **전제 조건(Prerequisites)**

- Python 3.11 이상
- Git
- OpenAI API 키

### 📦 **설치(Installation)**

**1. 레포지토리 클론**

```bash
git clone https://github.com/your-username/busan-chatbot-backend.git
cd busan-chatbot-backend
```

**2. 가상환경 생성 및 활성화**

```bash
python -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**3. 의존성 패키지 설치**

```bash
pip install -r requirements.txt
```

**4. 환경 변수 설정**
프로젝트 루트에 `.env` 파일 생성:

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
RENDER_DISK_PATH=./data  # 선택사항(개발환경)
```

### 🗄 **데이터베이스 초기화**

```bash
python -c "from app import app, db; from database.models import initialize_database; initialize_database(app)"
```

### ▶️ **서버 실행**

```bash
python app.py
```

서버는 `http://localhost:5001`에서 실행됩니다.

---

## 📡 API 엔드포인트(API Endpoints)

### 💬 **채팅 관련**

| Method   | Endpoint              | 설명        | Request Body                                                         | Response               |
|----------|-----------------------|-----------|----------------------------------------------------------------------|------------------------|
| `POST`   | `/api/chat`           | 채팅 메시지 처리 | `{"message": "string", "anonymousId": "string", "chatId": "string"}` | `{"reply": "AI 응답"}`   |
| `DELETE` | `/api/chat/<chat_id>` | 채팅 세션 삭제  | -                                                                    | `{"message": "삭제 완료"}` |

### 👤 **사용자 관련**

| Method | Endpoint                      | 설명          | Response                                     |
|--------|-------------------------------|-------------|----------------------------------------------|
| `GET`  | `/api/history/<anonymous_id>` | 사용자 채팅 히스토리 | `{chatId: {id, title, messages}}`            |
| `GET`  | `/api/users/stats`            | 전체 사용자 통계   | `{total_users, total_chats, total_messages}` |

### 🏢 **청년공간 관련**

| Method | Endpoint                               | 설명         | Response                            |
|--------|----------------------------------------|------------|-------------------------------------|
| `GET`  | `/api/spaces`                          | 전체 청년공간 목록 | `{success, data[], count, message}` |
| `GET`  | `/api/spaces/region/<region>`          | 지역별 청년공간   | `{success, data[], region}`         |
| `GET`  | `/api/spaces/search?keyword=<keyword>` | 키워드 검색     | `{success, data[], keyword}`        |
| `POST` | `/api/spaces/crawl`                    | 수동 크롤링 실행  | `{success, data[], crawled_at}`     |

### 📋 **청년 프로그램 관련**

| Method | Endpoint                                 | 설명          | Response                            |
|--------|------------------------------------------|-------------|-------------------------------------|
| `GET`  | `/api/programs`                          | 전체 모집중 프로그램 | `{success, data[], count, message}` |
| `GET`  | `/api/programs/region/<region>`          | 지역별 프로그램    | `{success, data[], region}`         |
| `GET`  | `/api/programs/search?keyword=<keyword>` | 키워드 검색      | `{success, data[], keyword}`        |
| `POST` | `/api/programs/crawl`                    | 수동 크롤링 실행   | `{success, data[], crawled_at}`     |

### 🔍 **시스템**

| Method | Endpoint  | 설명       | Response                          |
|--------|-----------|----------|-----------------------------------|
| `GET`  | `/health` | 시스템 헬스체크 | `{status, components, timestamp}` |

---

## 📁 프로젝트 구조(Project Structure)

```
busan-chatbot-backend/
├── 📄 app.py                          # 메인 실행 파일 (라우팅 전용)
├── 📄 requirements.txt                # 의존성 패키지 목록
├── 📄 .env                           # 환경 변수 설정
├── 📄 README.md                      # 프로젝트 문서
│
├── 📁 database/                      # 데이터베이스 관련
│   └── 📄 models.py                   # SQLAlchemy 모델 정의
│
├── 📁 config/                        # 설정 파일
│   └── 📄 predefined_answers.py       # 사전 정의 답변
│
├── 📁 services/                      # 외부 서비스 연동
│   ├── 📄 youth_space_crawler.py      # 청년공간 크롤링
│   └── 📄 youth_program_crawler.py    # 청년 프로그램 크롤링
│
├── 📁 handlers/                      # 비즈니스 로직 처리
│   ├── 📄 __init__.py
│   ├── 📄 chat_handler.py            # 채팅 관련 로직
│   ├── 📄 user_handler.py            # 사용자 관련 로직
│   ├── 📄 program_handler.py         # 프로그램 관련 로직
│   └── 📄 space_handler.py           # 공간 관련 로직
│
└── 📁 instance/                     # 데이터 저장소 (자동 생성)
    ├── 📄 chatbot.db                 # SQLite 데이터베이스
    ├── 📄 youth_spaces_cache.json    # 청년공간 캐시
    └── 📄 youth_programs_cache.json  # 프로그램 캐시
```

---

## 🎯 핵심 특징(Key Features)

### 🧩 **모듈러 아키텍처**

- **핸들러 기반 구조**: 기능별 비즈니스 로직 분리
- **단일 책임 원칙**: 각 모듈이 명확한 역할 담당
- **확장 가능성**: 새로운 기능 추가 시 독립적 개발 가능

### 🔄 **실시간 데이터 관리**

- **자동 캐싱**: 크롤링 데이터의 효율적 캐시 관리
- **캐시 만료**: 시간 기반 자동 데이터 갱신
- **수동 갱신**: 관리자의 수동 크롤링 지원

### 🔒 **안정성 & 성능**

- **에러 핸들링**: 포괄적인 예외 처리 및 로깅
- **CORS 지원**: 다양한 프론트엔드 환경 지원
- **SQLite 트랜잭션**: 데이터 무결성 보장

---

## 🌐 배포(Deployment)

### **Render 배포**

이 프로젝트는 Render에 최적화되어 있습니다:

1. **Build Command**: `pip install -r requirements.txt`
2. **Start Command**: `python app.py`
3. **Environment Variables**: `OPENAI_API_KEY` 설정 필요

### **로컬 개발**

```bash
python app.py
```

---

## 🤝 기여하기(Contributing)

1. 이 레포지토리를 Fork합니다
2. 새로운 기능 브랜치를 생성합니다 (`git checkout -b feature/새기능`)
3. 변경사항을 커밋합니다 (`git commit -am '새 기능 추가'`)
4. 브랜치에 Push합니다 (`git push origin feature/새기능`)
5. Pull Request를 생성합니다

---

## 📄 라이센스(License)

이 프로젝트는 MIT 라이센스 하에 배포됩니다.

---

## 📞 문의(Contact)

프로젝트에 대한 문의사항이나 버그 리포트는 GitHub Issues를 통해 제출해 주세요.

**부산시 청년들의 더 나은 정보 접근성을 위해 함께 만들어갑니다! 🚀**