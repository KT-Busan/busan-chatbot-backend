import os
import json
import openai
from datetime import datetime

from database.models import db, User, Chat, Message
from config.predefined_answers import PREDEFINED_ANSWERS
from services.youth_space_crawler import search_spaces_by_region, search_spaces_by_keyword
from services.youth_program_crawler import get_youth_programs_data, search_programs_by_region


class ChatHandler:
    def __init__(self):
        # OpenAI 클라이언트 초기화
        try:
            self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception as e:
            print(f"OpenAI 클라이언트 초기화 오류: {e}")
            self.client = None

        # 청년 공간 JSON 데이터 로드
        self.spaces_data = self.load_spaces_data()

    def load_spaces_data(self):
        """청년 공간 JSON 데이터 로드"""
        try:
            basedir = os.path.abspath(os.path.dirname(__file__))
            project_root = os.path.dirname(basedir)
            config_path = os.path.join(project_root, 'config')
            spaces_file = os.path.join(config_path, 'spaces_busan_youth.json')

            if os.path.exists(spaces_file):
                with open(spaces_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('spaces_busan_youth', [])
            else:
                print("spaces_busan_youth.json 파일을 찾을 수 없습니다.")
                return []
        except Exception as e:
            print(f"청년 공간 데이터 로드 오류: {e}")
            return []

    def search_spaces_by_keyword_json(self, keyword):
        """JSON 데이터에서 키워드로 공간 검색"""
        try:
            if not self.spaces_data:
                return f"청년 공간 데이터를 불러올 수 없습니다."

            # 키워드 매핑 (프론트엔드 버튼과 일치)
            keyword_mapping = {
                "스터디/회의": "📝 스터디/회의",
                "교육/강연": "🏫 교육/강연",
                "모임/커뮤니티": "👥 모임/커뮤니티",
                "진로/창업": "🚀 진로/창업",
                "문화/창작": "🎨 문화/창작",
                "작업/창작실": "💻 작업/창작실",
                "휴식/놀이": "🌿 휴식/놀이",
                "행사/이벤트": "🎬 행사/이벤트"
            }

            # 키워드 정규화
            search_keyword = keyword_mapping.get(keyword, keyword)

            filtered_spaces = []
            for space in self.spaces_data:
                # keywords 배열에서 검색
                if space.get('keywords'):
                    for space_keyword in space['keywords']:
                        if search_keyword in space_keyword or keyword in space_keyword:
                            filtered_spaces.append(space)
                            break

            if not filtered_spaces:
                return f"**{keyword}** 관련 청년공간을 찾을 수 없습니다.\n\n다른 키워드로 검색해보세요!"

            # 결과 포맷팅
            result = f"**{keyword}**로 찾은 공간입니다!\n\n"

            for i, space in enumerate(filtered_spaces[:10], 1):  # 최대 10개
                # 공간명 - 시설명 [지역] 형태
                result += f"{i}️⃣ **{space['space_name']}** - {space['parent_facility']} [{space['location']}]\n"

                # 추가 정보
                if space.get('capacity_min') and space.get('capacity_max'):
                    result += f"   👥 인원: {space['capacity_min']}~{space['capacity_max']}명\n"
                elif space.get('capacity_max'):
                    result += f"   👥 인원: 최대 {space['capacity_max']}명\n"

                if space.get('features'):
                    # features에서 가격 정보 추출
                    features = space['features']
                    if '무료' in features:
                        result += f"   💰 무료\n"
                    elif '유료' in features:
                        result += f"   💰 유료\n"

                result += "\n"

            result += "📌 **공간 상세 내용은**\n"
            result += "👉 \"청년 공간 상세\" 버튼을 눌러 확인하거나,\n"
            result += "👉 공간명을 입력해서 직접 확인해보세요!"

            return result

        except Exception as e:
            print(f"키워드 검색 오류: {e}")
            return "청년공간 검색 중 오류가 발생했습니다."

    def process_chat_message(self, user_message_text, anonymous_id, chat_id):
        """채팅 메시지 처리 (기존 로직 완벽 보존)"""
        if not self.client:
            return {"error": "OpenAI API 키가 설정되지 않았습니다."}, 500

        if not all([user_message_text, anonymous_id, chat_id]):
            return {"error": "필수 정보가 누락되었습니다."}, 400

        try:
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
            bot_reply = self.generate_bot_response(user_message_text, chat_id)

            # 봇 메시지 저장
            bot_message = Message(chat_id=chat_id, sender='bot', text=bot_reply)
            db.session.add(bot_message)
            db.session.commit()

            return {"reply": bot_reply}, 200

        except Exception as e:
            db.session.rollback()
            print(f"채팅 처리 오류: {e}")
            return {"error": "채팅 처리 중 오류가 발생했습니다."}, 500

    def delete_chat_session(self, chat_id):
        """채팅 세션 삭제"""
        try:
            chat_to_delete = Chat.query.filter_by(id=chat_id).first()
            if chat_to_delete:
                db.session.delete(chat_to_delete)
                db.session.commit()
                return {"message": "채팅이 성공적으로 삭제되었습니다."}, 200
            else:
                return {"error": "삭제할 채팅을 찾을 수 없습니다."}, 404
        except Exception as e:
            db.session.rollback()
            print(f"DB 삭제 오류: {e}")
            return {"error": "채팅 삭제 중 오류가 발생했습니다."}, 500

    def generate_bot_response(self, user_message_text, chat_id):
        """봇 응답 생성 로직 (기존 로직 100% 보존 + 청년 공간 예약 추가)"""

        # 0. 청년 공간 예약 처리 (새로 추가)
        if user_message_text == "청년 공간 예약":
            return """🏢 **청년 공간 예약**

부산시에는 다양한 청년을 위한 공간이 존재합니다!
목적에 맞게 다음 조건을 선택하여, 청년 공간을 대여해보세요!

아래에서 조건을 선택하신 후 검색해보세요! 👇"""

        # 1. 사전 정의된 질문 처리
        if user_message_text in PREDEFINED_ANSWERS:
            return PREDEFINED_ANSWERS[user_message_text]

        # 이전 대화 맥락 가져오기
        previous_messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at.desc()).limit(5).all()
        recent_context = "\n".join([msg.text for msg in previous_messages])

        # 2. "지역 프로그램" 형태 메시지 처리
        if " 프로그램" in user_message_text:
            region = user_message_text.replace(" 프로그램", "").strip()
            regions = ['중구', '동구', '서구', '영도구', '부산진구', '동래구', '연제구',
                       '금정구', '북구', '사상구', '사하구', '강서구', '남구', '해운대구', '수영구', '기장군']

            if region in regions:
                return search_programs_by_region(region)

        # 3. 지역별 검색 처리
        regions = ['중구', '동구', '서구', '영도구', '부산진구', '동래구', '연제구',
                   '금정구', '북구', '사상구', '사하구', '강서구', '남구', '해운대구', '수영구', '기장군']

        for region in regions:
            if user_message_text.strip() == region:  # 정확한 매칭으로 변경
                # 프로그램 맥락 확인
                program_context_keywords = ['프로그램 확인', 'PROGRAM_REGIONS', '프로그램이 있는지']
                has_program_context = any(keyword in recent_context for keyword in program_context_keywords)

                # 프로그램 키워드 확인
                program_keywords = ['프로그램', '교육', '강의', '과정', '모집', '신청', '바리스타', '취업', '컨설팅']
                has_program_keyword = any(keyword in user_message_text for keyword in program_keywords)

                if has_program_context or has_program_keyword:
                    return search_programs_by_region(region)
                else:
                    return search_spaces_by_region(region)

        # 4. 키워드 검색 처리 (JSON 데이터 사용으로 변경)
        keyword_list = ['스터디/회의', '교육/강연', '모임/커뮤니티', '진로/창업', '문화/창작', '작업/창작실', '휴식/놀이', '행사/이벤트']

        for keyword in keyword_list:
            if user_message_text.strip() == keyword:
                return self.search_spaces_by_keyword_json(keyword)

        # 5. 프로그램 관련 키워드 검색
        program_keywords = ['프로그램', '교육', '강의', '과정', '모집', '신청', '바리스타', '취업', '컨설팅']
        if any(keyword in user_message_text for keyword in program_keywords):
            try:
                programs = get_youth_programs_data()
                if programs:
                    result = f"**부산 청년 프로그램 모집중** ({len(programs)}개)\n\n"
                    for program in programs[:5]:
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

        # 6. 기타 키워드 검색 처리 (기존 크롤링 데이터 사용)
        if any(keyword in user_message_text for keyword in ['스터디', '창업', '회의', '카페', '라운지', '센터']):
            return search_spaces_by_keyword(user_message_text)

        # 7. OpenAI 호출
        try:
            all_previous_messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at.asc()).all()
            conversation_context = "\n".join(
                [f"{'사용자' if msg.sender == 'user' else '챗봇'}: {msg.text}" for msg in all_previous_messages])

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

            response = self.client.chat.completions.create(
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


# 전역 인스턴스 생성
chat_handler = ChatHandler()