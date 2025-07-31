import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import openai
from datetime import datetime
import requests
import re
import time
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import timedelta

from database.models import db, User, Chat, Message, initialize_database
from services.youth_space_crawler import search_spaces_by_region, search_spaces_by_keyword, get_all_youth_spaces


# --- 프로그램 크롤링 클래스 ---
class BusanYouthProgramCrawler:
    def __init__(self):
        self.base_url = "https://young.busan.go.kr"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def get_page_content(self, url, encoding='utf-8'):
        try:
            print(f"페이지 요청: {url}")
            response = self.session.get(url, timeout=15)
            response.encoding = encoding
            if response.status_code == 200:
                return BeautifulSoup(response.content, 'html.parser')
            print(f"HTTP 오류: {response.status_code}")
            return None
        except Exception as e:
            print(f"페이지 로드 오류: {e}")
            return None

    def extract_program_info_from_li(self, li_element):
        try:
            program_info = {
                'title': '',
                'region': '',
                'location': '',
                'status': '',
                'application_period': '',
                'link': ''
            }

            # 링크 추출
            link_element = li_element.select_one('a')
            if link_element:
                href = link_element.get('href', '')
                if href:
                    program_info['link'] = urljoin(self.base_url, href)

            # 모집 상태 확인 (모집중인 것만)
            recruit_state = li_element.select_one('.recruit_state .ing')
            if not recruit_state or recruit_state.get_text(strip=True) != '모집중':
                return None

            program_info['status'] = '모집중'

            # 제목 추출
            recruit_tit = li_element.select_one('.recruit_tit')
            if recruit_tit:
                title = recruit_tit.get_text(strip=True)
                program_info['title'] = title

                # 제목에서 지역 정보 추출
                region_match = re.search(r'\[([^]]+구)\]', title)
                if region_match:
                    program_info['region'] = region_match.group(1)

            # 신청기간 추출
            recruit_date = li_element.select_one('.recruit_date')
            if recruit_date:
                date_spans = recruit_date.find_all('span')
                if len(date_spans) >= 2:
                    date_text = date_spans[1].get_text(strip=True)
                    program_info['application_period'] = date_text

            # 장소/기관 정보 추출
            part3 = li_element.select_one('.part3')
            if part3:
                location_text = part3.get_text(strip=True)
                if location_text:
                    program_info['location'] = location_text

            if program_info['title'] and program_info['status'] == '모집중':
                return program_info
            return None

        except Exception as e:
            print(f"프로그램 정보 추출 오류: {e}")
            return None

    def crawl_all_programs(self):
        print("부산 청년 프로그램 크롤링 시작")
        all_programs = []

        for page in range(1, 6):  # 최대 5페이지
            print(f"페이지 {page} 크롤링 중...")

            if page == 1:
                url = "https://young.busan.go.kr/policySupport/act.nm?menuCd=261"
            else:
                url = f"https://young.busan.go.kr/policySupport/act.nm?menuCd=261&pageIndex={page}"

            soup = self.get_page_content(url)
            if not soup:
                continue

            program_list = soup.select('ul li')
            page_programs = []

            for li_element in program_list:
                if li_element.select_one('.recruit_state'):
                    program_info = self.extract_program_info_from_li(li_element)
                    if program_info:
                        page_programs.append(program_info)

            if not page_programs:
                print(f"페이지 {page}에서 프로그램을 찾을 수 없습니다.")
                break

            all_programs.extend(page_programs)
            print(f"페이지 {page}에서 {len(page_programs)}개 프로그램 수집")
            time.sleep(1)

        print(f"크롤링 완료: {len(all_programs)}개 모집중인 프로그램 수집")
        return all_programs


# --- 프로그램 데이터 관리 함수들 ---
def get_youth_programs_data():
    """청년 프로그램 데이터 가져오기 (캐시 포함)"""
    cache_file = os.path.join(instance_path, 'youth_programs_cache.json')
    cache_duration = timedelta(hours=6)  # 6시간 캐시

    # 캐시 파일 확인
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            cache_time = datetime.fromisoformat(cached_data['cached_at'])
            if datetime.now() - cache_time < cache_duration:
                print("캐시된 프로그램 데이터 사용")
                return cached_data['data']
        except Exception as e:
            print(f"캐시 읽기 오류: {e}")

    # 새로 크롤링
    print("🔄 새로운 프로그램 데이터 크롤링 중...")
    crawler = BusanYouthProgramCrawler()
    programs = crawler.crawl_all_programs()

    # 캐시 저장
    cache_data = {
        'cached_at': datetime.now().isoformat(),
        'data': programs
    }

    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print("프로그램 캐시 저장 완료")
    except Exception as e:
        print(f"캐시 저장 오류: {e}")

    return programs


def search_programs_by_region(region):
    """지역별 청년 프로그램 검색"""
    programs = get_youth_programs_data()
    if not programs:
        return "현재 청년 프로그램 정보를 가져올 수 없습니다."

    region_normalized = region.replace('구', '') if region.endswith('구') else region

    filtered_programs = []
    for program in programs:
        program_region = program.get('region', '')
        program_location = program.get('location', '')
        program_title = program.get('title', '')

        if (region_normalized in program_region or
                region_normalized in program_location or
                region_normalized in program_title):
            filtered_programs.append(program)

    if not filtered_programs:
        return f"**{region}**에서 현재 모집중인 청년 프로그램을 찾을 수 없습니다."

    result = f"**{region} 청년 프로그램** ({len(filtered_programs)}개 모집중)\n\n"

    for program in filtered_programs[:8]:
        result += format_program_info(program) + "\n"

    return result


def format_program_info(program):
    """프로그램 정보 포맷팅"""
    result = f"**{program['title']}**\n"
    result += f"🟢 {program['status']}\n"

    if program.get('application_period'):
        result += f"📅 신청기간: {program['application_period']}\n"

    if program.get('location'):
        result += f"📍 장소: {program['location']}\n"

    if program.get('link'):
        result += f"🔗 [자세히 보기]({program['link']})\n"

    return result


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

# --- 5. 부산 청년 공간 관련 사전 정의 답변 ---
PREDEFINED_ANSWERS = {
    "지역별 확인하기": "[REGION_MAP]🗺️ **부산 청년공간 지도**\n\n지도에서 원하는 지역을 클릭하시거나, 아래 지역 목록에서 선택해주세요!\n각 지역별로 청년공간 개수를 확인할 수 있어요.",
    "키워드별 확인하기": "🔍 **키워드 검색**을 이용해보세요!\n\n예시: '스터디', '창업', '회의실', '카페' 등\n궁금한 키워드를 입력해주세요!",
    "청년 공간 프로그램 확인하기": "예시 답변입니다.",
    "청년 공간 예약": "예시 답변입니다.",
    "안녕": "안녕하세요! 부산 청년 공간을 알리는 B-BOT입니다! 🤖\n\n청년 공간 관련 궁금한 것이 있으시면 무엇이든 물어보세요!",
    "안녕하세요": "안녕하세요! 부산 청년 공간을 알리는 B-BOT입니다! 🤖\n\n청년 공간 관련 궁금한 것이 있으시면 무엇이든 물어보세요!",
}


# --- 6. 새로운 프로그램 관련 API 엔드포인트 ---
@app.route('/api/programs', methods=['GET'])
def get_programs():
    """전체 프로그램 목록 API"""
    try:
        programs = get_youth_programs_data()
        return jsonify({
            'success': True,
            'data': programs,
            'count': len(programs),
            'message': f'{len(programs)}개의 모집중인 프로그램을 찾았습니다.'
        })
    except Exception as e:
        print(f"프로그램 API 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '프로그램 정보를 가져오는 중 오류가 발생했습니다.'
        }), 500


@app.route('/api/programs/region/<region>', methods=['GET'])
def get_programs_by_region_api(region):
    """지역별 프로그램 검색 API"""
    try:
        result = search_programs_by_region(region)
        programs = get_youth_programs_data()

        # 해당 지역 프로그램 필터링
        region_normalized = region.replace('구', '') if region.endswith('구') else region
        filtered_programs = []
        for program in programs:
            program_region = program.get('region', '')
            program_location = program.get('location', '')
            program_title = program.get('title', '')

            if (region_normalized in program_region or
                    region_normalized in program_location or
                    region_normalized in program_title):
                filtered_programs.append(program)

        return jsonify({
            'success': True,
            'data': filtered_programs,
            'count': len(filtered_programs),
            'message': result,
            'region': region
        })
    except Exception as e:
        print(f"지역별 프로그램 API 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'{region} 지역의 프로그램 정보를 가져오는 중 오류가 발생했습니다.'
        }), 500


@app.route('/api/programs/crawl', methods=['POST'])
def crawl_programs_now():
    """즉시 프로그램 크롤링 API (테스트용)"""
    try:
        print("수동 크롤링 요청 받음")
        crawler = BusanYouthProgramCrawler()
        programs = crawler.crawl_all_programs()

        # 캐시에 저장
        cache_data = {
            'cached_at': datetime.now().isoformat(),
            'data': programs
        }

        cache_file = os.path.join(instance_path, 'youth_programs_cache.json')
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

        return jsonify({
            'success': True,
            'data': programs,
            'count': len(programs),
            'message': f'크롤링 완료! {len(programs)}개의 모집중인 프로그램을 수집했습니다.',
            'crawled_at': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"수동 크롤링 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '크롤링 중 오류가 발생했습니다.'
        }), 500


# --- 7. 기존 API 엔드포인트들 ---
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

    if len(chat_session.messages) == 0 and user_message_text not in PREDEFINED_ANSWERS:
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

    # 1. 사전 정의된 질문 처리
    if user_message_text in PREDEFINED_ANSWERS:
        return PREDEFINED_ANSWERS[user_message_text]

    # 2. 지역별 청년공간 검색 처리
    regions = ['중구', '동구', '서구', '영도구', '부산진구', '동래구', '연제구',
               '금정구', '북구', '사상구', '사하구', '강서구', '남구', '해운대구', '수영구', '기장군']

    for region in regions:
        if region in user_message_text:
            # 프로그램 관련 키워드가 함께 있는지 확인
            program_keywords = ['프로그램', '교육', '강의', '과정', '모집', '신청', '바리스타', '취업', '컨설팅']
            if any(keyword in user_message_text for keyword in program_keywords):
                return search_programs_by_region(region)
            else:
                return search_spaces_by_region(region)

    # 3. 프로그램 관련 키워드 검색 처리
    program_keywords = ['프로그램', '교육', '강의', '과정', '모집', '신청', '바리스타', '취업', '컨설팅']
    if any(keyword in user_message_text for keyword in program_keywords):
        try:
            programs = get_youth_programs_data()
            if programs:
                result = f"**부산 청년 프로그램 모집중** ({len(programs)}개)\n\n"
                for program in programs[:5]:  # 상위 5개만
                    result += f"🟢 **{program['title']}**\n"
                    if program.get('application_period'):
                        result += f"📅 {program['application_period']}\n"
                    if program.get('location'):
                        result += f"📍 {program['location']}\n"
                    result += "\n"
                if len(programs) > 5:
                    result += f"... 외 {len(programs) - 5}개 프로그램 더 있음\n\n"
                result += "💡 지역명과 함께 질문하시면 해당 지역 프로그램을 찾아드려요!"
                return result
        except Exception as e:
            print(f"프로그램 검색 오류: {e}")

    # 4. 키워드 검색 처리 (공간명, 설명에서 검색)
    if any(keyword in user_message_text for keyword in ['스터디', '창업', '회의', '카페', '라운지', '센터']):
        return search_spaces_by_keyword(user_message_text)

    # 5. OpenAI 호출
    try:
        # 이전 대화 맥락 가져오기
        previous_messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at.asc()).all()
        conversation_context = "\n".join(
            [f"{'사용자' if msg.sender == 'user' else '챗봇'}: {msg.text}" for msg in previous_messages])

        system_prompt = f"""
# 페르소나 (Persona)
너는 부산시 청년들을 위한 청년 공간 정보 전문가, **'B-BOT'**이다. 너의 목표는 청년들의 청년 공간 관련 질문에 **명확하고, 정확하며, 도움이 되는 정보**를 제공하여 그들이 청년 공간을 잘 활용할 수 있도록 돕는 것이다.

# 핵심 지침 (Core Instructions)
1. **정보 제공 우선순위:** 
   - **1순위: 부산 청년 공간 관련 정보** (부산청년센터, 청년두드림카페, 소담스퀘어 등)
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


if __name__ == "__main__":
    initialize_database(app)
    app.run(host='0.0.0.0', port=5001, debug=True)
else:
    initialize_database(app)