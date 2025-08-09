# 🤖 부산 청년 챗봇 백엔드

부산시 청년들을 위한 AI 기반 청년공간 및 프로그램 정보 제공 챗봇 백엔드 시스템

## 🎯 프로젝트 개요

부산시 청년들이 청년공간과 프로그램 정보를 쉽게 찾을 수 있도록 도와주는 AI 챗봇의 백엔드 서버입니다. OpenAI GPT-4를 활용한 자연어 처리와 웹 크롤링을 통한 실시간 정보 수집을 제공합니다.

### 🌟 주요 특징

- **AI 기반 대화**: OpenAI GPT-4o를 활용한 자연스러운 대화
- **실시간 정보**: 웹 크롤링을 통한 최신 청년공간 및 프로그램 정보
- **Override 시스템**: 수동으로 수정된 정보를 자동으로 병합
- **조건별 검색**: 지역, 인원, 목적별 맞춤 공간 검색
- **캐시 시스템**: 효율적인 데이터 관리 및 성능 최적화

## 🚀 주요 기능

- 청년공간 정보 서비스
- 청년 프로그램 정보 서비스
- AI 챗봇 서비스
- 데이터 관리

## 🛠 기술 스택

- **Framework**: Flask 3.x
- **Database**: SQLite (SQLAlchemy ORM)
- **AI**: OpenAI GPT-4o
- **Web Crawling**: BeautifulSoup4, Requests
- **Environment**: Python 3.9+

### Infrastructure

- **Deployment**: Render
- **Storage**: Render Disk Storage
- **Environment Management**: python-dotenv

## 📁 프로젝트 구조

```
busan-chatbot-backend/
├── 📁 config/                      # 설정 파일
│   ├── predefined_answers.py       # 미리 정의된 답변
│   └── spaces_busan_youth.json     # 청년공간 기본 데이터
├── 📁 database/                    # 데이터베이스 관련
│   └── models.py                   # SQLAlchemy 모델 정의
├── 📁 handlers/                    # 비즈니스 로직 핸들러
│   ├── chat_handler.py            # 채팅 처리 핸들러
│   ├── program_handler.py         # 프로그램 정보 핸들러
│   ├── space_handler.py           # 공간 정보 핸들러
│   └── user_handler.py            # 사용자 관리 핸들러
├── 📁 instance/                    # 런타임 데이터 저장소
│   ├── chatbot.db                 # SQLite 데이터베이스
│   ├── youth_programs_cache.json  # 프로그램 캐시
│   ├── youth_spaces_cache.json    # 공간 캐시
│   └── youth_spaces_overrides.json # 공간 Override 데이터
├── 📁 services/                    # 외부 서비스 연동
│   ├── youth_program_crawler.py   # 프로그램 크롤러
│   └── youth_space_crawler.py     # 공간 크롤러
├── 📄 app.py                      # Flask 애플리케이션 메인
├── 📄 requirements.txt            # Python 의존성
└── 📄 README.md                   # 프로젝트 문서
```

## 🔧 설치 및 실행

### 1. 저장소 클론

```bash
git clone https://github.com/your-repo/busan-chatbot-backend.git
cd busan-chatbot-backend
```

### 2. 가상환경 설정

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정

```bash
# .env 파일 생성
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

### 5. 애플리케이션 실행

```bash
python app.py
```

## 🌐 API 문서

| 카테고리            | 엔드포인트                                        | 메소드    | 설명               |
|-----------------|----------------------------------------------|--------|------------------|
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
|                 | `/api/spaces/crawl`                          | POST   | 수동 크롤링           |
|                 | `/api/spaces/all`                            | GET    | 전체 공간 목록 (포맷된)   |
|                 | `/api/spaces/busan-youth`                    | GET    | 부산 청년공간 데이터      |
| **청년 프로그램**     | `/api/programs`                              | GET    | 전체 프로그램 목록       |
|                 | `/api/programs/region/{region}`              | GET    | 지역별 프로그램 검색      |
|                 | `/api/programs/search?keyword={keyword}`     | GET    | 키워드 검색           |
|                 | `/api/programs/crawl`                        | POST   | 수동 크롤링           |
| **Override 관리** | `/api/spaces/overrides/status`               | GET    | Override 상태 확인   |
|                 | `/api/spaces/overrides/reload`               | POST   | Override 데이터 재로드 |
|                 | `/api/spaces/overrides/test/{region}`        | GET    | 지역별 Override 테스트 |
|                 | `/api/spaces/overrides/compare/{space_name}` | GET    | 공간 데이터 비교        |
| **디버깅**         | `/api/debug/spaces-status`                   | GET    | 공간 데이터 상태 확인     |
|                 | `/api/debug/reload-spaces`                   | POST   | 공간 데이터 강제 재로드    |
|                 | `/api/spaces/region/{region}/debug`          | GET    | 지역별 검색 (디버그)     |
| **헬스체크**        | `/health`                                    | GET    | 시스템 상태 확인        |
|                 | `/api/health`                                | GET    | 상세 시스템 상태        |

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

---

**🎉 부산 청년들의 더 나은 공간 활용을 위해!**