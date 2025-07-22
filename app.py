import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import openai
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

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


# --- 6. API 엔드포인트 정의 ---
# 사용자의 전체 채팅 기록을 불러오는 API
@app.route("/api/history/<anonymous_id>", methods=["GET"])
def get_history(anonymous_id):
    user = User.query.filter_by(anonymous_id=anonymous_id).first()
    if not user:
        return jsonify({})

    chats = Chat.query.filter_by(user_id=user.id).order_by(Chat.created_at.desc()).all()

    history = {}
    for chat in chats:
        messages = [{'sender': msg.sender, 'text': msg.text} for msg in chat.messages]
        history[chat.id] = {
            'id': chat.id,
            'title': chat.title,
            'messages': messages
        }
    return jsonify(history)


# 채팅 메시지를 처리하고 DB에 저장하는 API
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

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": "너는 부산시의 청년 지원 정책과 일자리 정보를 전문적으로 알려주는 친절한 챗봇이야. 이름은 '부산 청년 지원 전문가'야. 항상 부산시의 청년 입장에서, 정확한 정보를 바탕으로 답변해줘."},
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


# --- 7. 서버 실행 ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # 앱 실행 시 데이터베이스 테이블이 없으면 생성
    app.run(host='0.0.0.0', port=5001, debug=True)