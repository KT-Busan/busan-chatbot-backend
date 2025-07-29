import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import openai
from datetime import datetime

from database.models import db, User, Chat, Message, JobPosting, initialize_database
from services.scraper_service import get_busanjob_latest_jobs
from services.data_service import get_job_postings_from_db, get_external_data
from config.predefined_answers import PREDEFINED_ANSWERS

# --- 1. 기본 설정 및 라이브러리 초기화 ---
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(os.environ.get('RENDER_DISK_PATH', basedir), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

app = Flask(__name__)

# --- 2. 데이터베이스 설정 ---
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "chatbot.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


# --- 3. CORS 헤더 수동 추가 ---
@app.after_request
def after_request(response):
    allowed_origins = [
        'http://localhost:5173',  # Vite 개발 서버
        'http://localhost:3000',  # Create React App 개발 서버
        'http://127.0.0.1:5173',  # 로컬 IP
        'http://127.0.0.1:3000',  # 로컬 IP
        'https://kt-busan.github.io'  # 프로덕션 배포
    ]
    origin = request.headers.get('Origin')
    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)

    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


# --- 4. OpenAI 클라이언트 초기화 ---
try:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    print(f"OpenAI 클라이언트 초기화 오류: {e}")
    client = None


# --- 5. API 엔드포인트 정의 ---
@app.route("/api/history/<anonymous_id>", methods=["GET"])
def get_history(anonymous_id):
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

    # 사용자 확인/생성
    user = User.query.filter_by(anonymous_id=anonymous_id).first()
    if not user:
        user = User(anonymous_id=anonymous_id)
        db.session.add(user)
        db.session.commit()

    # 채팅 세션 확인/생성
    chat_session = Chat.query.filter_by(id=chat_id).first()
    if not chat_session:
        chat_session = Chat(id=chat_id, user_id=user.id, title=user_message_text)
        db.session.add(chat_session)

    if len(chat_session.messages) == 0 and user_message_text not in PREDEFINED_ANSWERS and user_message_text != "현재 모집 중인 일자리 지원 사업":
        chat_session.title = user_message_text

    # 사용자 메시지 저장
    user_message = Message(chat_id=chat_id, sender='user', text=user_message_text)
    db.session.add(user_message)
    db.session.commit()

    # 봇 응답 생성
    bot_reply = generate_bot_response(user_message_text, chat_id, client)

    # 봇 메시지 저장
    bot_message = Message(chat_id=chat_id, sender='bot', text=bot_reply)
    db.session.add(bot_message)
    db.session.commit()

    return jsonify({"reply": bot_reply})


@app.route("/api/chat/<chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    try:
        chat_to_delete = Chat.query.filter_by(id=chat_id).first()
        if chat_to_delete:
            db.session.delete(chat_to_delete)
            db.session.commit()
            return jsonify({"message": "채팅이 성공적으로 삭제되었습니다."}), 200
        else:
            return jsonify({"error": "삭제할 채팅을 찾을 수 없습니다."}), 404
    except Exception as e:
        db.session.rollback()
        print(f"DB 삭제 오류: {e}")
        return jsonify({"error": "채팅 삭제 중 오류가 발생했습니다."}), 500


def generate_bot_response(user_message_text, chat_id, client):
    """봇 응답 생성 로직"""

    # 1. '현재 모집 중인 일자리 지원 사업' 버튼 클릭 시
    if user_message_text == "현재 모집 중인 일자리 지원 사업":
        return get_job_postings_from_db()

    # 2. 사전 정의된 질문 클릭 시 (이 부분을 2번으로 올려야 함!)
    if user_message_text in PREDEFINED_ANSWERS:
        return PREDEFINED_ANSWERS[user_message_text]

    # 3. 'Busan Jobs' 스크래핑 요청 시 (순서 변경 및 조건 수정)
    if user_message_text in ["최신 채용정보", "부산잡 채용정보", "채용공고"] or \
            any(keyword in user_message_text.lower() for keyword in ["최신", "채용", "구인"]):
        return get_busanjob_latest_jobs()

    # 4. DB에서 특정 사업명 검색
    all_postings = JobPosting.query.all()
    found_post = None
    for post in all_postings:
        if post.title in user_message_text or user_message_text in post.title:
            found_post = post
            break

    if found_post:
        details = found_post.details if found_post.details else "별도의 상세 정보가 없습니다."
        link = found_post.link if found_post.link else ""
        bot_reply = f"✅ **'{found_post.title}'**에 대한 상세 정보입니다.\n\n"
        bot_reply += f"**🎯 지원 대상:** {found_post.target}\n"
        bot_reply += f"**📋 상세 내용:** {details}\n"
        if found_post.phone:
            bot_reply += f"**📞 문의 전화:** {found_post.phone}\n"
        if found_post.email:
            bot_reply += f"**📧 문의 이메일:** {found_post.email}\n"
        if link:
            bot_reply += f"\n[**🔗 더 자세한 내용 보러가기**]({link})"
        return bot_reply

    # 5. OpenAI 호출
    try:
        # 이전 대화 맥락 가져오기
        previous_messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at.asc()).all()
        conversation_context = "\n".join(
            [f"{'사용자' if msg.sender == 'user' else '챗봇'}: {msg.text}" for msg in previous_messages])

        # DB에서 관련 정보 검색 (RAG)
        search_terms = user_message_text.split()
        relevant_postings = set()
        for term in search_terms:
            posts = JobPosting.query.filter(JobPosting.title.like(f'%{term}%')).limit(2).all()
            for post in posts:
                relevant_postings.add(f"사업명: {post.title}, 지원대상: {post.target}, 상세정보: {post.details}")

        realtime_data = "\n".join(list(relevant_postings))

        # 외부 API 데이터 추가
        external_info = get_external_data(user_message_text)
        if external_info:
            realtime_data += f"\n{external_info}"

        system_prompt = f"""
# 페르소나 (Persona)
너는 부산시 청년들을 위한 정책 및 일자리 정보 전문가, **'B-BOT'**이다. 너의 목표는 청년들의 질문에 **명확하고, 정확하며, 희망을 주는 정보**를 제공하여 그들의 든든한 가이드가 되는 것이다.

# 핵심 지침 (Core Instructions)
1. **정보 활용 우선순위:** 
   - **1순위: [실시간 외부 정보]**: 이 정보가 존재할 경우, 반드시 이 내용을 기반으로 답변을 구성하라.
   - **2순위: [이전 대화 맥락]**: 대화의 흐름을 파악하고 사용자의 이전 질문과 관련된 답변을 할 때 참고하라.
   - **3순위: 너의 일반 지식**: 위 정보들로 답변할 수 없는 일반적인 질문이나 대화에만 너의 내부 지식을 사용하라.

2. **정확성과 정직성:**
   - 주어진 정보에 명시되지 않은 내용은 절대로 추측하지 마라.
   - 모르는 정보에 대해서는 솔직하게 말하고 유용한 대안을 제시하라.

3. **어조 및 스타일:**
   - 항상 긍정적이고 친절하며, 청년들을 격려하고 응원하는 따뜻한 말투를 유지하라.
   - 사용자의 상황에 공감하며 대화하는 느낌을 주어야 한다.

# 출력 형식 (Output Formatting)
- 모든 답변은 **마크다운(Markdown)**을 사용하여 구조화하라.
- **핵심 정보**는 `**굵은 글씨**`로 강조하라.
- **항목 나열** 시에는 글머리 기호(`-` 또는 `*`)를 사용하라.
- **링크 제공** 시에는 전체 URL 주소를 보여주라.

# 참고 자료 (Context)
---
[실시간 외부 정보]
{realtime_data if realtime_data else "관련된 실시간 정보가 없습니다."}

[이전 대화 맥락]
{conversation_context if conversation_context else "아직 대화 기록이 없습니다."}
---
"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message_text}
            ]
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"OpenAI API 오류: {e}")
        return "죄송합니다, 답변 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."


# --- 6. 서버 실행 ---
if __name__ == "__main__":
    initialize_database(app)
    app.run(host='0.0.0.0', port=5001, debug=True)
else:
    initialize_database(app)
