import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import openai
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import requests
import re

DB_PATH = os.path.join('/data', 'chatbot.db')

# --- 1. 기본 설정 및 라이브러리 초기화 ---
load_dotenv()

# 데이터베이스 경로 문제 해결을 위한 수정
basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

app = Flask(__name__)

# --- 2. 데이터베이스 설정 ---
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# --- 3. CORS 헤더 수동 추가 ---
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


class JobPosting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(50))
    title = db.Column(db.Text, nullable=False)
    period = db.Column(db.String(100))
    organization = db.Column(db.Text)
    schedule = db.Column(db.Text)
    phone = db.Column(db.String(100))
    email = db.Column(db.String(100))
    target = db.Column(db.Text)
    details = db.Column(db.Text)
    link = db.Column(db.Text)
    end_date = db.Column(db.Date)


# --- 5. OpenAI 클라이언트 초기화 ---
try:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    print(f"OpenAI 클라이언트 초기화 오류: {e}")
    client = None

# --- 6. 사전 정의 답변 (새로운 UI에 맞게 수정) ---
PREDEFINED_ANSWERS = {
    # 메인 메뉴 답변
    "부산청년센터 대관 이용 수칙": (
        "대관 신청 전 꼭 확인해야 할 핵심 유의사항을 알려드릴게요.\n\n"
        "* **신청 대상:** 청년(단체)이 주최하고 청년을 대상으로 하는 비상업적, 비정치적, 비종교적 행사만 가능해요.\n"
        "* **신청 기간:** 평일 기준 최소 3일 전까지 신청해야 하며, 최대 2개월 이내의 날짜만 선택할 수 있어요.\n"
        "* **제한 사항:** 상품 판매를 목적으로 하거나, 센터 시설을 훼손할 우려가 있는 행사는 대관이 제한될 수 있습니다.\n\n"
        "더 자세한 전체 유의사항은 [부산청년센터](https://young.busan.go.kr/bycenter/index.nm?menuCd=158) 링크에서 꼭 확인해주세요!"
    ),
    "부산청년센터 장소 대여": (
        "부산청년센터에서는 청년들의 활동을 지원하기 위해 다양한 공간을 무료로 대여해드리고 있어요.\n\n"
        "**어떤 공간들이 있나요?**\n"
        "* **다목적홀:** 강연, 공연, 소규모 행사 등을 위한 공간 (최대 50명)\n"
        "* **세미나실:** 스터디, 회의, 동아리 활동에 적합한 공간 (최대 12명)\n"
        "* **영상 스튜디오:** 유튜브 촬영, 온라인 강의 제작이 가능한 전문 장비 보유 공간\n\n"
        "**어떻게 신청하나요?**\n"
        "모든 대관 신청은 온라인으로만 가능하며, 이용일 기준 최소 3일 전까지 예약을 완료해야 합니다.\n\n"
        "아래 링크에서 원하는 공간과 시간을 선택하여 직접 예약할 수 있어요.\n\n"
        "[부산청년센터 대관하기](https://young.busan.go.kr/bycenter/centerPlace/list.nm?menuCd=132)"
    ),
    "현재 모집 중인 일자리 지원 사업": (
        "부산시의 최신 청년 일자리 지원 사업 정보는 부산청년플랫폼 사이트에서 가장 정확하게 확인하실 수 있어요.\n\n"
        "아래 링크로 접속하시면 현재 모집 중인 사업 공고 전체를 마감일 순서대로 보실 수 있습니다.\n\n"
        "[현재 모집 중인 사업 보러가기](https://young.busan.go.kr/policySupport/list.nm)"
    ),

    # 추천 질문 답변
    "청년 센터 일정": "오늘은 **'AI 전문가 초청 특강'**이 오후 2시에 예정되어 있습니다. 자세한 내용은 홈페이지를 참고해주세요!",
    "청년 센터 이용 수칙": "부산청년센터 이용 시에는 다음 수칙을 지켜주세요:\n* 음식물 반입은 지정된 공간에서만 가능합니다.\n* 사용하신 공간은 깨끗하게 정리해주세요.\n* 다른 이용자에게 방해가 되지 않도록 주의해주세요.",
    "청년 센터 운영 시간": "부산청년센터는 **평일 오전 9시부터 오후 9시까지**, **토요일은 오전 10시부터 오후 6시까지** 운영됩니다. 일요일과 공휴일은 휴관입니다.",
    "FAQ": """자주 묻는 질문(FAQ) 목록입니다.\n1. **모든 프로그램은 무료인가요?**\n   네, 대부분의 프로그램은 무료이지만, 일부 재료비가 필요한 클래스는 소정의 참가비가 있을 수 있습니다.\n2. **부산 시민만 이용할 수 있나요?**\n   아니요, 부산시에 거주하거나 활동하는 청년(만 18세~39세)이라면 누구나 이용 가능합니다.\n3. **주차는 가능한가요?**\n   아쉽지만, 별도의 주차 공간은 마련되어 있지 않습니다. 대중교통 이용을 부탁드립니다.""",

    # 간단한 인사말 추가
    "안녕": "안녕하세요! 저는 부산 청년들을 위한 챗봇 B-BOT입니다. 무엇이든 물어보세요!",
    "안녕?": "안녕하세요! 저는 부산 청년들을 위한 챗봇 B-BOT입니다. 무엇이든 물어보세요!",
    "안녕하세요": "안녕하세요! 저는 부산 청년들을 위한 챗봇 B-BOT입니다. 무엇이든 물어보세요!",
    "안녕하세요?": "안녕하세요! 저는 부산 청년들을 위한 챗봇 B-BOT입니다. 무엇이든 물어보세요!",
}


# --- 7. DB에서 일자리 정보를 조회하는 함수 ---
def get_job_postings_from_db():
    with app.app_context():
        today = date.today()
        postings = JobPosting.query.filter(JobPosting.end_date >= today) \
            .order_by(JobPosting.end_date.asc()) \
            .limit(3).all()
        if not postings:
            return "현재 모집 중인 일자리 지원 사업을 찾지 못했어요. 관리자가 데이터를 업데이트할 때까지 기다려주세요!"

        result_text = "현재 모집 중인 사업 중 마감이 임박한 3개 사업을 알려드릴게요!\n\n"
        for post in postings:
            result_text += f"**- 사업명:** {post.title}\n"
            result_text += f"  - **담당 기관:** {post.organization}\n"
            result_text += f"  - **신청 기간:** {post.period}\n"
            # 지원 대상 정보 추가 (50자까지 요약)
            if post.target:
                target_summary = (post.target[:50] + '...') if len(post.target) > 50 else post.target
                result_text += f"  - **지원 대상:** {target_summary}\n"
            result_text += "\n"

        result_text += "더 자세한 정보는 사업명을 포함해서 질문해주시거나, [부산청년플랫폼](https://young.busan.go.kr/policySupport/list.nm)에서 확인하실 수 있습니다."
        return result_text


# --- 8. 외부 오픈 API 호출 함수 ---
def get_external_data(user_query):
    if "날씨" in user_query:
        API_KEY = os.getenv("OPENWEATHER_API_KEY")
        if not API_KEY:
            return "날씨 API 키가 설정되지 않았습니다."
        BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
        params = {'q': 'Busan', 'appid': API_KEY, 'lang': 'kr', 'units': 'metric'}
        try:
            response = requests.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            description = data['weather'][0]['description']
            temp = data['main']['temp']
            return f"현재 부산 날씨는 '{description}'이며, 기온은 {temp}°C 입니다."
        except requests.exceptions.RequestException as e:
            print(f"날씨 API 호출 오류: {e}")
            return "날씨 정보를 가져오는 데 실패했습니다."
    return None


# --- 9. API 엔드포인트 정의 ---
@app.route("/api/history/<anonymous_id>", methods=["GET"])
def get_history(anonymous_id):
    user = User.query.filter_by(anonymous_id=anonymous_id).first()
    if not user: return jsonify({})
    chats = Chat.query.filter_by(user_id=user.id).order_by(Chat.created_at.desc()).all()
    history = {}
    for chat in chats:
        messages = [{'sender': msg.sender, 'text': msg.text} for msg in chat.messages]
        history[chat.id] = {'id': chat.id, 'title': chat.title, 'messages': messages}
    return jsonify(history)


@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == 'OPTIONS': return jsonify({'status': 'ok'}), 200
    if not client: return jsonify({"error": "OpenAI API 키가 설정되지 않았습니다."}), 500

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
    if len(chat_session.messages) == 0 and user_message_text not in PREDEFINED_ANSWERS and user_message_text != "현재 모집 중인 일자리 지원 사업":
        chat_session.title = user_message_text

    user_message = Message(chat_id=chat_id, sender='user', text=user_message_text)
    db.session.add(user_message)
    db.session.commit()

    bot_reply = None
    # 1. '현재 모집 중인 일자리 지원 사업' 버튼 클릭 시
    if user_message_text == "현재 모집 중인 일자리 지원 사업":
        bot_reply = get_job_postings_from_db()
    # 2. 다른 사전 정의된 질문 클릭 시
    elif user_message_text in PREDEFINED_ANSWERS:
        bot_reply = PREDEFINED_ANSWERS[user_message_text]

    # 3. 위 두 경우가 아니면, DB에서 특정 사업명 검색 또는 OpenAI 호출
    if bot_reply is None:
        # DB에서 사용자가 언급한 사업명이 있는지 검색
        all_postings = JobPosting.query.all()
        found_post = None
        for post in all_postings:
            # 사업명의 일부만 포함되어도 찾을 수 있도록 in 연산자 사용
            if post.title in user_message_text or user_message_text in post.title:
                found_post = post
                break

        if found_post:
            # 특정 사업 정보를 찾았다면, 상세 정보를 답변으로 구성
            details = found_post.details if found_post.details else "별도의 상세 정보가 없습니다."
            link = found_post.link if found_post.link else ""
            bot_reply = f"네, **'{found_post.title}'**에 대한 상세 정보입니다.\n\n"
            bot_reply += f"**- 지원 대상:** {found_post.target}\n"
            bot_reply += f"**- 상세 내용:** {details}\n"
            if link:
                bot_reply += f"\n더 자세한 내용은 [여기]({link})를 클릭해서 확인해보세요!"

    if bot_reply is None:
        # OpenAI 호출 로직
        previous_messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at.asc()).all()
        conversation_context = "\n".join(
            [f"{'사용자' if msg.sender == 'user' else '챗봇'}: {msg.text}" for msg in previous_messages])

        # DB에서 관련 정보 검색 (간단한 RAG)
        search_terms = user_message_text.split()
        relevant_postings = set()
        for term in search_terms:
            posts = JobPosting.query.filter(JobPosting.title.like(f'%{term}%')).limit(2).all()
            for post in posts:
                relevant_postings.add(f"사업명: {post.title}, 지원대상: {post.target}, 상세정보: {post.details}")

        realtime_data = "\n".join(list(relevant_postings))

        system_prompt = f"""
# 페르소나 (Persona)
너는 부산시 청년들을 위한 정책 및 일자리 정보 전문가, **'B-BOT'**이다. 너의 목표는 청년들의 질문에 **명확하고, 정확하며, 희망을 주는 정보**를 제공하여 그들의 든든한 가이드가 되는 것이다.

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
        except Exception as e:
            print(f"API 오류: {e}")
            bot_reply = "죄송합니다, 답변 생성 중 오류가 발생했습니다."

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


# --- 9. 서버 실행 ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5001, debug=True)
