import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import openai
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests

# --- 1. 기본 설정 및 라이브러리 초기화 ---
load_dotenv()
app = Flask(__name__)

# --- 2. 데이터베이스 설정 ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# --- 3. CORS 헤더 수동 추가 (기존 코드 유지) ---
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


# --- 4. 데이터베이스 테이블 모델 정의 ---
# (User, Chat, Message 모델 정의는 이전과 동일)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    anonymous_id = db.Column(db.String(120), unique=True, nullable=False)
    chats = db.relationship('Chat', backref='user', lazy=True, cascade="all, delete-orphan")


class Chat(db.Model):
    id = db.Column(db.String(120), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('Message', backref='chat', lazy=True, cascade="all, delete-orphan")


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(120), db.ForeignKey('chat.id'), nullable=False)
    sender = db.Column(db.String(50), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# --- 5. OpenAI 클라이언트 초기화 ---
try:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    print(f"OpenAI 클라이언트 초기화 오류: {e}")
    client = None

# 6. 카테고리별 사전 정의 답변 추가
PREDEFINED_ANSWERS = {
    "오늘의 부산청년센터 대한 일정": "오늘은 **'AI 전문가 초청 특강'**이 오후 2시에 예정되어 있습니다. 자세한 내용은 홈페이지를 참고해주세요!",
    "부산청년센터 대한 이용수칙": "부산청년센터 이용 시에는 다음 수칙을 지켜주세요:\n* 음식물 반입은 지정된 공간에서만 가능합니다.\n* 사용하신 공간은 깨끗하게 정리해주세요.\n* 다른 이용자에게 방해가 되지 않도록 주의해주세요.",
    "부산청년 기쁨두배통장 신청 안내": "**부산청년 기쁨두배통장**은 매년 상반기에 모집하며, 신청 자격은 부산시에 거주하는 만 18세 이상 34세 이하의 근로 청년입니다. 자세한 공고는 부산청년플랫폼 사이트를 확인해주세요.",
    "모집 중인 청년 지원 사업": "현재 모집 중인 주요 사업은 **'청년 월세 지원 사업'**과 **'면접 정장 대여 서비스'**가 있습니다. 각 사업별 세부 조건이 다르니 공고문을 꼭 확인해보세요!",
    "부산청년센터 운영 시간": "부산청년센터는 **평일 오전 9시부터 오후 9시까지**, **토요일은 오전 10시부터 오후 6시까지** 운영됩니다. 일요일과 공휴일은 휴관입니다.",
    "모집 중인 부산청년센터 프로그램": "현재 **'취업 역량 강화 스터디'**와 **'원데이 클래스-도자기 공예'** 프로그램의 참여자를 모집하고 있습니다. 센터에 방문하여 신청하실 수 있습니다."
}


# --- 7. 외부 오픈 API 호출 함수 (기존 코드 유지) ---
def get_external_data(user_query):
    # ... (이전과 동일한 코드)
    return None


# --- 8. API 엔드포인트 정의 ---
@app.route("/api/history/<anonymous_id>", methods=["GET"])
def get_history(anonymous_id):
    # (이전과 동일한 코드)
    user = User.query.filter_by(anonymous_id=anonymous_id).first()
    if not user:
        return jsonify({})
    chats = Chat.query.filter_by(user_id=user.id).order_by(Chat.created_at.desc()).all()
    history = {}
    for chat in chats:
        messages = [{'sender': msg.sender, 'text': msg.text} for msg in chat.messages]
        history[chat.id] = {'id': chat.id, 'title': chat.title, 'messages': messages}
    return jsonify(history)


@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    if not client:
        return jsonify({"error": "OpenAI API 키가 설정되지 않았습니다."}), 500

    data = request.get_json()
    user_message_text = data.get("message")
    anonymous_id = data.get("anonymousId")
    chat_id = data.get("chatId")

    if not all([user_message_text, anonymous_id, chat_id]):
        return jsonify({"error": "필수 정보가 누락되었습니다."}), 400

    user = User.query.filter_by(anonymous_id=anonymous_id).first()
    if not user:
        user = User(anonymous_id=anonymous_id)
        db.session.add(user)
        db.session.commit()

    chat_session = Chat.query.filter_by(id=chat_id).first()
    if not chat_session:
        chat_session = Chat(id=chat_id, user_id=user.id, title=user_message_text)
        db.session.add(chat_session)
    if len(chat_session.messages) == 0:
        chat_session.title = user_message_text

    user_message = Message(chat_id=chat_id, sender='user', text=user_message_text)
    db.session.add(user_message)
    db.session.commit()

    # 사전 정의된 질문인지 먼저 확인하는 로직 추가
    if user_message_text in PREDEFINED_ANSWERS:
        bot_reply = PREDEFINED_ANSWERS[user_message_text]

        # DB에 봇 답변 저장
        bot_message = Message(chat_id=chat_id, sender='bot', text=bot_reply)
        db.session.add(bot_message)
        db.session.commit()

        # 미리 준비된 답변을 즉시 반환
        return jsonify({"reply": bot_reply})

    # 사전 정의된 질문이 아닐 경우에만 아래 OpenAI 호출 로직 실행

    # (프롬프트 엔지니어링 및 OpenAI 호출 로직은 이전과 동일)
    previous_messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at.asc()).all()
    conversation_context = "\n".join(
        [f"{'사용자' if msg.sender == 'user' else '챗봇'}: {msg.text}" for msg in previous_messages])
    realtime_data = get_external_data(user_message_text)
    system_prompt = f"""
    # 페르소나 (Persona)
    너는 부산시 청년들을 위한 정책 및 일자리 정보 전문가, **'부산 청년 지원 전문가'**이다. 너의 목표는 청년들의 질문에 **명확하고, 정확하며, 희망을 주는 정보**를 제공하여 그들의 든든한 가이드가 되는 것이다.

    # 핵심 지침 (Core Instructions)
    1.  **정보 활용 우선순위:** 너는 답변을 생성할 때 반드시 아래의 우선순위를 따라야 한다.
        - **1순위: [실시간 외부 정보]**: 이 정보가 존재할 경우, 반드시 이 내용을 기반으로 답변을 구성하라. 이것이 가장 정확한 최신 정보이다.
        - **2순위: [이전 대화 맥락]**: 대화의 흐름을 파악하고 사용자의 이전 질문과 관련된 답변을 할 때 참고하라.
        - **3순위: 너의 일반 지식**: 위 정보들로 답변할 수 없는 일반적인 질문이나 대화에만 너의 내부 지식을 사용하라.

    2.  **정확성과 정직성:**
        - 주어진 [참고 자료]에 명시되지 않은 내용은 절대로 추측하여 답변하지 마라.
        - 모르는 정보에 대해서는 **"죄송하지만, 문의하신 내용에 대한 정확한 정보가 없습니다. 괜찮으시다면 부산청년플랫폼(young.busan.go.kr)에서 추가 정보를 확인해 보시는 것을 추천드려요."** 와 같이 솔직하고 유용한 대안을 제시하라.

    3.  **어조 및 스타일:**
        - 항상 긍정적이고 친절하며, 청년들을 격려하고 응원하는 따뜻한 말투를 유지하라.
        - 딱딱한 정보 전달이 아닌, 사용자의 상황에 공감하며 대화하는 느낌을 주어야 한다.

    # 출력 형식 (Output Formatting)
    - 모든 답변은 사용자가 읽기 쉽도록 반드시 **마크다운(Markdown)**을 사용하여 구조화하라.
    - **핵심 정보**(사업명, 지원 금액, 신청 기간 등)는 `**굵은 글씨**`로 강조하여 가독성을 높여라. (예: **최대 20만원**)
    - **항목 나열** 시에는 반드시 글머리 기호(`-` 또는 `*`)를 사용하여 목록을 만들어라.
    - **링크 제공** 시에는 전체 URL 주소(`https://...`)를 그대로 보여주어 사용자가 신뢰하고 클릭할 수 있게 하라.

    # 보안 및 주제 제한 (Security & Topic Restriction)
    - 개인정보(이름, 연락처, 주민번호 등)를 절대 묻거나 저장하려고 시도하지 마라.
    - 정치, 종교 등 관련 없는 주제는 **"저는 청년 정책과 일자리 정보를 전문적으로 안내해 드리는 챗봇입니다. 해당 주제에 대해서는 답변해 드리기 어려운 점 양해 부탁드려요."** 와 같이 정중하게 거절하라.

    # 참고 자료 (Context)
    ---
    [실시간 외부 정보]
    {realtime_data if realtime_data else "관련된 실시간 정보가 없습니다."}

    [이전 대화 맥락]
    {conversation_context if conversation_context else "아직 대화 기록이 없습니다."}
    ---
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message_text}
            ]
        )
        bot_reply = response.choices[0].message.content

        bot_message = Message(chat_id=chat_id, sender='bot', text=bot_reply)
        db.session.add(bot_message)
        db.session.commit()

        return jsonify({"reply": bot_reply})
    except Exception as e:
        print(f"API 오류: {e}")
        return jsonify({"error": "답변 생성 중 오류 발생"}), 500


# --- 9. 서버 실행 ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5001, debug=True)