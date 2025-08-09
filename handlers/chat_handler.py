import os
import json
import openai
import random
from datetime import datetime

from database.models import db, User, Chat, Message
from config.predefined_answers import PREDEFINED_ANSWERS
from services.youth_space_crawler import search_spaces_by_region, search_spaces_by_keyword
from services.youth_program_crawler import get_youth_programs_data, search_programs_by_region


class ChatHandler:
    def __init__(self):
        try:
            self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception:
            self.client = None

        self.spaces_data = self.load_spaces_data()
        self.keyword_mapping = self._init_keyword_mapping()
        self.purpose_mapping = self._init_purpose_mapping()

    def _init_keyword_mapping(self):
        """키워드 매핑 초기화"""
        return {
            "📝스터디/회의": ["📝스터디/회의", "📝 스터디/회의", "스터디/회의", "스터디", "회의"],
            "🎤교육/강연": ["🎤교육/강연", "🏫교육/강연", "🏫 교육/강연", "교육/강연", "교육", "강연"],
            "👥커뮤니티": ["👥커뮤니티", "👥모임/커뮤니티", "👥 모임/커뮤니티", "모임/커뮤니티", "커뮤니티", "모임"],
            "🚀진로/창업": ["🚀진로/창업", "🚀 진로/창업", "진로/창업", "진로", "창업"],
            "🎨문화/창작": ["🎨문화/창작", "🎨 문화/창작", "문화/창작", "문화", "창작"],
            "🛠작업/창작실": ["🛠작업/창작실", "💻작업/창작실", "💻 작업/창작실", "작업/창작실", "작업", "창작실"],
            "🧘휴식/놀이": ["🧘휴식/놀이", "🌿휴식/놀이", "🌿 휴식/놀이", "휴식/놀이", "휴식", "놀이"],
            "🎪행사/이벤트": ["🎪행사/이벤트", "🎬행사/이벤트", "🎬 행사/이벤트", "행사/이벤트", "행사", "이벤트"]
        }

    def _init_purpose_mapping(self):
        """목적 매핑 초기화"""
        return {
            '스터디/회의': ['📝스터디/회의', '📝 스터디/회의', '스터디', '회의'],
            '교육/강연': ['🎤교육/강연', '🏫교육/강연', '🏫 교육/강연', '교육', '강연'],
            '커뮤니티': ['👥커뮤니티', '👥모임/커뮤니티', '👥 모임/커뮤니티', '커뮤니티', '모임'],
            '진로/창업': ['🚀진로/창업', '🚀 진로/창업', '진로', '창업'],
            '문화/창작': ['🎨문화/창작', '🎨 문화/창작', '문화', '창작'],
            '작업/창작실': ['🛠작업/창작실', '💻작업/창작실', '💻 작업/창작실', '작업', '창작실'],
            '휴식/놀이': ['🧘휴식/놀이', '🌿휴식/놀이', '🌿 휴식/놀이', '휴식', '놀이'],
            '행사/이벤트': ['🎪행사/이벤트', '🎬행사/이벤트', '🎬 행사/이벤트', '행사', '이벤트']
        }

    def load_spaces_data(self):
        """spaces_busan_youth.json 데이터 로드"""
        try:
            basedir = os.path.abspath(os.path.dirname(__file__))
            project_root = os.path.dirname(basedir)
            config_path = os.path.join(project_root, 'config')
            spaces_file = os.path.join(config_path, 'spaces_busan_youth.json')

            if os.path.exists(spaces_file):
                with open(spaces_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('spaces_busan_youth', [])
            return []
        except Exception:
            return []

    def format_space_detail(self, space):
        """청년 공간 상세 정보 포맷팅"""
        try:
            parent_facility = space.get('parent_facility', '정보없음')
            space_name = space.get('space_name', '정보없음')
            location = space.get('location', '정보없음')
            introduction = space.get('introduction', '정보없음')
            eligibility = space.get('eligibility', '정보없음')
            features = space.get('features', '정보없음')

            capacity_info = self.format_capacity_info(space)
            link_url = self.extract_link_url(space.get('link'))

            result = f"🟩 **{parent_facility} - {space_name}** - {location}\n"
            result += f"🎯 **한 줄 소개:** {introduction}\n"
            result += f"• 📍 **위치:** {location}\n"
            result += f"• 👥 **인원:** {capacity_info}\n"
            result += f"• **지원 대상:** {eligibility}\n"
            result += f"• 🧰 **특징:** {features}\n"

            if link_url != '정보없음':
                result += f"• 🔗 **링크:** {link_url}\n"

            return result

        except Exception:
            return "공간 정보를 불러오는 중 오류가 발생했습니다."

    def extract_link_url(self, link):
        """링크 URL 추출"""
        if isinstance(link, list) and len(link) > 0:
            return link[0]
        elif isinstance(link, str):
            return link
        return '정보없음'

    def format_capacity_info(self, space):
        """인원 정보 포맷팅"""
        capacity_min = space.get('capacity_min')
        capacity_max = space.get('capacity_max')

        if capacity_min and capacity_max:
            return f"최소 {capacity_min}명 ~ 최대 {capacity_max}명"
        elif capacity_max:
            return f"최대 {capacity_max}명"
        elif capacity_min:
            return f"최소 {capacity_min}명"
        else:
            return "인원 제한 없음"

    def find_matching_spaces(self, user_input):
        """사용자 입력과 매칭되는 공간 찾기"""
        if not self.spaces_data:
            return []

        user_input_lower = user_input.lower()
        matching_spaces = []

        for space in self.spaces_data:
            space_name = space.get('space_name', '').lower()
            parent_facility = space.get('parent_facility', '').lower()

            if (space_name in user_input_lower or
                    user_input_lower in space_name or
                    parent_facility in user_input_lower or
                    user_input_lower in parent_facility):
                matching_spaces.append(space)

        return matching_spaces

    def handle_space_detail_request(self, user_input):
        """청년 공간 상세 요청 처리"""
        try:
            if not self.spaces_data:
                return "❌ 청년 공간 데이터를 불러올 수 없습니다."

            matching_spaces = self.find_matching_spaces(user_input)

            if matching_spaces:
                result = f"**🔍 '{user_input}' 검색 결과**\n\n"

                for i, space in enumerate(matching_spaces[:5], 1):
                    result += f"**{i}.** "
                    result += self.format_space_detail(space)
                    result += "\n"

                if len(matching_spaces) > 5:
                    result += f"... 외 {len(matching_spaces) - 5}개 공간 더 있음\n"

                return result

            return self.show_all_spaces_detail()

        except Exception:
            return "청년 공간 상세 정보를 불러오는 중 오류가 발생했습니다."

    def show_all_spaces_detail(self):
        """모든 청년 공간을 상세 포맷으로 표시"""
        try:
            result = "**🏢 부산 청년 공간 상세 정보**\n\n"
            result += "아래 공간들 중 원하는 공간명을 입력하시면 더 자세한 정보를 확인할 수 있습니다!\n\n"

            regions = {}
            for space in self.spaces_data:
                location = space.get('location', '기타')
                regions.setdefault(location, []).append(space)

            for region, spaces in list(regions.items())[:3]:
                result += f"**📍 {region}**\n"

                for space in spaces[:2]:
                    result += self.format_space_detail(space)
                    result += "\n"

                if len(spaces) > 2:
                    result += f"... 외 {len(spaces) - 2}개 공간 더 있음\n\n"
                else:
                    result += "\n"

            total_spaces = len(self.spaces_data)
            total_regions = len(regions)

            if total_regions > 3:
                result += f"... 외 {total_regions - 3}개 지역 더 있음\n\n"

            result += f"💡 총 **{total_spaces}개**의 청년 공간이 있습니다.\n"
            result += "**특정 공간명을 입력**하시면 해당 공간의 상세 정보를 확인할 수 있어요!\n\n"
            result += "🔍 **검색 예시:**\n"
            result += "• \"커뮤니티룸\" - 커뮤니티룸 관련 공간들\n"
            result += "• \"부산청년센터\" - 부산청년센터 관련 공간들\n"
            result += "• \"회의실\" - 회의실이 있는 공간들"

            return result

        except Exception:
            return "청년 공간 목록을 불러오는 중 오류가 발생했습니다."

    def search_spaces_by_keyword_json(self, keyword):
        """JSON 데이터에서 키워드로 공간 검색"""
        try:
            if not self.spaces_data:
                return "❌ 청년 공간 데이터를 불러올 수 없습니다."

            search_keywords = self.keyword_mapping.get(keyword, [keyword])
            filtered_spaces = []

            for space in self.spaces_data:
                space_keywords = space.get('keywords', [])

                for search_kw in search_keywords:
                    for space_kw in space_keywords:
                        if search_kw.lower() in space_kw.lower() or space_kw.lower() in search_kw.lower():
                            filtered_spaces.append(space)
                            break
                    else:
                        continue
                    break

            if not filtered_spaces:
                return (f"**{keyword}** 관련 청년공간을 찾을 수 없습니다.\n\n다른 키워드로 검색해보세요!\n\n"
                        f"💡 **사용 가능한 키워드:**\n"
                        f"- 📝스터디/회의\n- 🎤교육/강연\n- 👥커뮤니티\n- 🚀진로/창업\n"
                        f"- 🎨문화/창작\n- 🛠작업/창작실\n- 🧘휴식/놀이\n- 🎪행사/이벤트")

            result = f"**{keyword}**로 찾은 공간입니다!\n\n"

            for i, space in enumerate(filtered_spaces, 1):
                parent_facility = space.get('parent_facility', '정보없음')
                space_name = space.get('space_name', '정보없음')
                location = space.get('location', '정보없음')
                result += f"**{i}.** {parent_facility} - {space_name} [{location}]\n"

            result += "\n📌 **공간 상세 내용은**\n"
            result += "👉 \"청년 공간 상세\" 버튼을 눌러 확인하거나,\n"
            result += "👉 공간명을 입력해서 직접 확인해보세요!"

            return result

        except Exception:
            return "청년공간 검색 중 오류가 발생했습니다."

    def parse_search_conditions(self, search_text):
        """검색 조건 파싱"""
        conditions = {}
        try:
            search_part = search_text.split("조건별 검색:", 1)[1].strip()

            for condition in search_part.split("|"):
                if "=" in condition:
                    key, value = condition.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    if key == "지역":
                        conditions['region'] = value
                    elif key == "인원":
                        conditions['capacity'] = value
                    elif key == "목적":
                        conditions['purpose'] = value
        except Exception:
            pass

        return conditions

    def handle_space_reservation_search(self, conditions):
        """조건별 청년 공간 검색"""
        try:
            region = conditions.get('region', '').strip()
            capacity = conditions.get('capacity', '').strip()
            purpose = conditions.get('purpose', '').strip()

            if not any([region, capacity, purpose]):
                return "❌ 지역, 인원, 이용 목적 중 하나는 반드시 선택해주세요."

            condition_display = []
            if region: condition_display.append(f"지역 : {region}")
            if capacity: condition_display.append(f"인원 : {capacity}")
            if purpose: condition_display.append(f"목적 : {purpose}")

            filtered_spaces = self.filter_spaces_by_conditions(region, capacity, purpose)

            if not filtered_spaces:
                return self.format_no_results_message(region, capacity, purpose)

            result = f"✅ **선택하신 조건**\n"
            for condition in condition_display:
                result += f"• {condition}\n"
            result += f"\n🔎 **조건에 맞는 공간을 찾고 있어요...**\n\n"

            return self.format_search_results(filtered_spaces, region, capacity, purpose)

        except Exception:
            return "검색 중 오류가 발생했습니다. 다시 시도해주세요."

    def filter_spaces_by_conditions(self, region, capacity, purpose):
        """조건에 따른 공간 필터링"""
        filtered_spaces = []

        for space in self.spaces_data:
            conditions_met = []

            if region:
                if space.get('location') == region:
                    conditions_met.append('region')
                else:
                    continue

            if capacity:
                if self.check_capacity_match(space, capacity):
                    conditions_met.append('capacity')
                else:
                    continue

            if purpose:
                if self.check_purpose_match(space, purpose):
                    conditions_met.append('purpose')
                else:
                    continue

            selected_conditions = []
            if region: selected_conditions.append('region')
            if capacity: selected_conditions.append('capacity')
            if purpose: selected_conditions.append('purpose')

            if set(selected_conditions) == set(conditions_met):
                space_copy = space.copy()
                space_copy['match_score'] = len(conditions_met)
                space_copy['match_reasons'] = []
                if region: space_copy['match_reasons'].append(f"지역: {region}")
                if capacity: space_copy['match_reasons'].append(f"인원: {capacity}")
                if purpose: space_copy['match_reasons'].append(f"목적: {purpose}")
                filtered_spaces.append(space_copy)

        return filtered_spaces

    def check_capacity_match(self, space, selected_capacity):
        """인원 조건 매칭 확인"""
        try:
            capacity_min = space.get('capacity_min')
            capacity_max = space.get('capacity_max')

            if not capacity_min and not capacity_max:
                return True

            capacity_checks = {
                '1-2명': lambda: capacity_min is None or capacity_min <= 2,
                '3-6명': lambda: (capacity_min is None or capacity_min <= 6) and (
                        capacity_max is None or capacity_max >= 3),
                '7명이상': lambda: capacity_max is None or capacity_max >= 7,
                '상관없음': lambda: True
            }

            return capacity_checks.get(selected_capacity, lambda: False)()

        except Exception:
            return True

    def check_purpose_match(self, space, selected_purpose):
        """목적 조건 매칭 확인"""
        try:
            space_keywords = space.get('keywords', [])
            if not space_keywords:
                return False

            search_keywords = self.purpose_mapping.get(selected_purpose, [selected_purpose])

            for search_kw in search_keywords:
                for space_kw in space_keywords:
                    if search_kw.lower() in space_kw.lower() or space_kw.lower() in search_kw.lower():
                        return True

            return False
        except Exception:
            return False

    def format_search_results(self, spaces, region, capacity, purpose):
        """검색 결과 포맷팅"""
        try:
            spaces.sort(key=lambda x: x.get('match_score', 0), reverse=True)

            result = f"📌 **총 {len(spaces)}개의 공간**을 찾았어요!\n\n"
            result += "---\n\n"

            for i, space in enumerate(spaces, 1):
                result += f"**{i}️⃣ {space.get('parent_facility', '정보없음')} – {space.get('space_name', '정보없음')}**\n"
                result += f"{space.get('introduction', '정보없음')}\n"
                result += f"• 📍 **위치 :** {space.get('location', '정보없음')}\n"
                result += f"• 👥 **인원 :** {self.format_capacity_info(space)}\n"
                result += f"• **지원 대상 :** {space.get('eligibility', '정보없음')}\n"
                result += f"• 🧰 **특징 :** {space.get('features', '정보없음')}\n"

                link_url = self.extract_link_url(space.get('link'))
                if link_url != '정보없음':
                    result += f"• 🔗 **링크 :** {link_url}\n"

                result += "\n---\n\n"

            result += "[SHOW_CONDITIONAL_SEARCH_BUTTONS]"
            return result

        except Exception:
            return "검색 결과를 표시하는 중 오류가 발생했습니다."

    def format_no_results_message(self, region, capacity, purpose):
        """결과 없음 메시지 포맷팅"""
        conditions = []
        if region: conditions.append(f"지역: {region}")
        if capacity: conditions.append(f"인원: {capacity}")
        if purpose: conditions.append(f"목적: {purpose}")

        condition_text = ", ".join(conditions)

        result = f"😥 **{condition_text}** 조건에 맞는 청년공간을 찾을 수 없습니다.\n\n"
        result += "💡 **다른 조건으로 검색해보세요!**\n"
        result += "• 지역 조건을 넓혀보거나\n"
        result += "• 인원 조건을 '상관없음'으로 변경하거나\n"
        result += "• 다른 이용 목적을 선택해보세요\n\n"
        result += "[🔄 새로 검색하기] 버튼을 눌러 다시 시도하세요!"

        return result

    def handle_random_recommendation(self):
        """랜덤 추천 처리"""
        try:
            if not self.spaces_data:
                return "추천할 청년공간 정보를 불러올 수 없습니다."

            random_space = random.choice(self.spaces_data)

            result = "🎲 **랜덤으로 추천해드릴게요!**\n\n"
            result += f"**1️⃣ {random_space.get('parent_facility', '정보없음')} – {random_space.get('space_name', '정보없음')}**\n"
            result += f"{random_space.get('introduction', '정보없음')}\n"
            result += f"• 📍 **위치 :** {random_space.get('location', '정보없음')}\n"
            result += f"• 👥 **인원 :** {self.format_capacity_info(random_space)}\n"
            result += f"• **지원 대상 :** {random_space.get('eligibility', '정보없음')}\n"
            result += f"• 🧰 **특징 :** {random_space.get('features', '정보없음')}\n"

            link_url = self.extract_link_url(random_space.get('link'))
            if link_url != '정보없음':
                result += f"• 🔗 **링크 :** {link_url}\n"

            result += "\n---\n\n"
            result += "[SHOW_ADDITIONAL_RANDOM]"

            return result

        except Exception:
            return "랜덤 추천 중 오류가 발생했습니다."

    def process_chat_message(self, user_message_text, anonymous_id, chat_id):
        """채팅 메시지 처리"""
        if not self.client:
            return {"error": "OpenAI API 키가 설정되지 않았습니다."}, 500

        if not all([user_message_text, anonymous_id, chat_id]):
            return {"error": "필수 정보가 누락되었습니다."}, 400

        try:
            user = User.query.filter_by(anonymous_id=anonymous_id).first()
            if not user:
                user = User(anonymous_id=anonymous_id)
                db.session.add(user)
                db.session.commit()

            chat_session = Chat.query.filter_by(id=chat_id).first()
            if not chat_session:
                chat_session = Chat(id=chat_id, user_id=user.id, title=user_message_text)
                db.session.add(chat_session)

            if len(chat_session.messages) == 0 and user_message_text not in PREDEFINED_ANSWERS:
                chat_session.title = user_message_text

            user_message = Message(chat_id=chat_id, sender='user', text=user_message_text)
            db.session.add(user_message)
            db.session.commit()

            bot_reply = self.generate_bot_response(user_message_text, chat_id)

            bot_message = Message(chat_id=chat_id, sender='bot', text=bot_reply)
            db.session.add(bot_message)
            db.session.commit()

            return {"reply": bot_reply}, 200

        except Exception:
            db.session.rollback()
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
        except Exception:
            db.session.rollback()
            return {"error": "채팅 삭제 중 오류가 발생했습니다."}, 500

    def generate_bot_response(self, user_message_text, chat_id):
        """봇 응답 생성 로직"""
        special_commands = {
            "청년 공간 상세": "[SPACE_DETAIL_SEARCH]",
            "청년 공간 프로그램 확인하기": "[PROGRAM_REGIONS]",
            "✨ 랜덤 추천": self.handle_random_recommendation()
        }

        if user_message_text in special_commands:
            command_result = special_commands[user_message_text]
            return command_result() if callable(command_result) else command_result

        if "조건별 검색:" in user_message_text:
            try:
                conditions = self.parse_search_conditions(user_message_text)
                return self.handle_space_reservation_search(conditions)
            except Exception:
                return "검색 조건 처리 중 오류가 발생했습니다."

        if " 프로그램" in user_message_text:
            region = user_message_text.replace(" 프로그램", "").strip()
            regions = ['중구', '동구', '서구', '영도구', '부산진구', '동래구', '연제구',
                       '금정구', '북구', '사상구', '사하구', '강서구', '남구', '해운대구', '수영구', '기장군']

            if region in regions:
                return search_programs_by_region(region)

        regions = ['중구', '동구', '서구', '영도구', '부산진구', '동래구', '연제구',
                   '금정구', '북구', '사상구', '사하구', '강서구', '남구', '해운대구', '수영구', '기장군']

        if user_message_text.strip() in regions:
            return search_spaces_by_region(user_message_text.strip())

        keyword_list = list(self.keyword_mapping.keys())
        if user_message_text.strip() in keyword_list:
            return self.search_spaces_by_keyword_json(user_message_text.strip())

        old_keyword_mapping = {
            '스터디/회의': '📝스터디/회의', '교육/강연': '🎤교육/강연',
            '모임/커뮤니티': '👥커뮤니티', '진로/창업': '🚀진로/창업',
            '문화/창작': '🎨문화/창작', '작업/창작실': '🛠작업/창작실',
            '휴식/놀이': '🧘휴식/놀이', '행사/이벤트': '🎪행사/이벤트'
        }

        if user_message_text.strip() in old_keyword_mapping:
            new_keyword = old_keyword_mapping[user_message_text.strip()]
            return self.search_spaces_by_keyword_json(new_keyword)

        if any(keyword in user_message_text for keyword in ['스터디', '창업', '회의', '카페', '라운지', '센터']):
            return search_spaces_by_keyword(user_message_text)

        try:
            all_previous_messages = Message.query.filter_by(chat_id=chat_id).order_by(
                Message.created_at.asc()).all()
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

        except Exception:
            return "죄송합니다, 답변 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."


chat_handler = ChatHandler()