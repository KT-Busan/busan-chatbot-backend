#  Busan Chatbot - Backend

부산시 청년들을 위한 정책 및 일자리 정보 제공 챗봇의 백엔드 서버입니다. 이 서버는 사용자의 질문을 받아 OpenAI의 대규모 언어 모델(LLM)과 상호작용하고, 대화 내용을 데이터베이스에 저장 및 관리하는 역할을 합니다.

---

## 주요 기능(Features)

-   **챗봇 API**: 사용자의 메시지를 받아 OpenAI GPT-4o 모델을 통해 답변을 생성
-   **프롬프트 엔지니어링**: 페르소나, 규칙, 참고 자료(Context)를 포함하는 정교한 시스템 프롬프트를 통해 답변 품질을 제어
-   **사전 정의 답변**: 자주 묻는 질문(카테고리)에 대해 API 호출 없이 즉각적인 답변을 제공하여 속도와 일관성을 확보
-   **대화 기록 관리**: SQLite 데이터베이스를 사용하여 사용자별 대화 기록을 영구적으로 저장, 조회, 삭제
-   **외부 API 연동**: 특정 키워드(예: "날씨")에 반응하여 외부 오픈 API를 호출하고, 실시간 정보를 챗봇 답변에 활용

---

## 기술 스택(Tech Stack)

-   **Language**: Python 3.11+
-   **Framework**: Flask
-   **Database**: SQLite
-   **ORM**: Flask-SQLAlchemy
-   **External API**: OpenAI API
-   **Libraries**: `python-dotenv`, `requests`, `flask-cors`

---

## 시작하기(Getting Started)

로컬 환경에서 이 프로젝트를 설정하고 실행하는 방법

### 1. 전제 조건(Prerequisites)

-   Python 3.11 이상
-   Git

### 2. 설치(Installation)

1.  **레포지토리 클론:**
    ```bash
    git clone <YOUR_REPOSITORY_URL>
    cd busan-chatbot-backend
    ```

2.  **가상환경 생성 및 활성화:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # macOS/Linux
    # venv\Scripts\activate   # Windows
    ```

3.  **의존성 패키지 설치:**
    * (최초 1회) 현재 설치된 패키지 목록으로 `requirements.txt` 파일 생성:
        ```bash
        pip freeze > requirements.txt
        ```
    * 생성된 파일로 패키지 설치:
        ```bash
        pip install -r requirements.txt
        ```

4.  **환경 변수 설정:**
    -   프로젝트 루트에 `.env` 파일을 생성
    -   아래 내용을 파일에 작성하고, 본인의 OpenAI API 키를 입력 (외부 API를 사용한다면 해당 키도 추가)
        ```
        OPENAI_API_KEY="sk-..."
        # OPENWEATHER_API_KEY="your-weather-api-key"
        ```

### 3. 데이터베이스 초기화

-   (최초 1회) `app.py`에 정의된 모델에 따라 `chatbot.db` 파일을 생성
    ```bash
    # 터미널에서 Python 셸 실행
    python
    ```
    ```python
    # Python 셸 내부에서 실행
    >>> from app import app, db
    >>> with app.app_context():
    ...     db.create_all()
    ...
    >>> exit()
    ```

### 4. 서버 실행(Running the Application)

```bash
python app.py
```
-   서버는 `http://localhost:5001` 에서 실행

---

## API 엔드포인트(API Endpoints)

| Method | Endpoint                      | 설명                       | 요청 Body (JSON)                                    | 성공 응답 (JSON)                                       |
| :----- | :---------------------------- |:-------------------------| :-------------------------------------------------- | :----------------------------------------------------- |
| `GET`  | `/api/history/<anonymous_id>` | 특정 사용자의 전체 대화 기록을 조회     | 없음                                                | `{ chatId: { id, title, messages } }` 형태의 객체      |
| `POST` | `/api/chat`                   | 새 메시지를 보내고 챗봇의 답변을 받음    | `{ "message", "anonymousId", "chatId" }`            | `{ "reply": "챗봇의 답변 내용" }`                      |
| `DELETE`| `/api/chat/<chat_id>`         | 특정 대화 세션 전체를 DB에서 삭제 | 없음                                                | `{ "message": "채팅이 성공적으로 삭제되었습니다." }` |