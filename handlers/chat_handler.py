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

    def format_space_detail(self, space):
        """청년 공간 상세 정보를 새로운 포맷으로 변환"""
        try:
            parent_facility = space.get('parent_facility', '정보없음')
            space_name = space.get('space_name', '정보없음')
            location = space.get('location', '정보없음')
            introduction = space.get('introduction', '정보없음')
            eligibility = space.get('eligibility', '정보없음')
            capacity_min = space.get('capacity_min')
            capacity_max = space.get('capacity_max')
            features = space.get('features', '정보없음')
            link = space.get('link', [])

            # 링크 처리 (배열인 경우 첫 번째 링크 사용)
            if isinstance(link, list) and len(link) > 0:
                link_url = link[0]
            elif isinstance(link, str):
                link_url = link
            else:
                link_url = '정보없음'

            # 인원 정보 포맷팅
            if capacity_min and capacity_max:
                capacity_info = f"최소 {capacity_min}명 ~ 최대 {capacity_max}명"
            elif capacity_max:
                capacity_info = f"최대 {capacity_max}명"
            elif capacity_min:
                capacity_info = f"최소 {capacity_min}명"
            else:
                capacity_info = "인원 제한 없음"

            # 포맷된 결과 생성
            result = f"🟩 **{parent_facility} - {space_name}** - {location}\n"
            result += f"🎯 **한 줄 소개:** {introduction}\n"
            result += f"• 📍 **위치:** {location}\n"
            result += f"• 👥 **인원:** {capacity_info}\n"
            result += f"• **지원 대상:** {eligibility}\n"
            result += f"• 🧰 **특징:** {features}\n"

            if link_url != '정보없음':
                result += f"• 🔗 **링크:** {link_url}\n"

            return result

        except Exception as e:
            print(f"공간 상세 포맷팅 오류: {e}")
            return "공간 정보를 불러오는 중 오류가 발생했습니다."

    def handle_space_detail_request(self, user_input):
        """청년 공간 상세 요청 처리"""
        try:
            print(f"🏢 청년 공간 상세 요청 처리 시작")
            print(f"📊 로드된 데이터 개수: {len(self.spaces_data)}")

            if not self.spaces_data:
                return "❌ 청년 공간 데이터를 불러올 수 없습니다."

            # 사용자가 특정 공간명을 입력했는지 확인
            user_input_lower = user_input.lower()

            # 특정 공간명이 포함된 경우
            matching_spaces = []
            for space in self.spaces_data:
                space_name = space.get('space_name', '').lower()
                parent_facility = space.get('parent_facility', '').lower()

                # 공간명 또는 시설명으로 검색
                if (space_name in user_input_lower or
                        user_input_lower in space_name or
                        parent_facility in user_input_lower or
                        user_input_lower in parent_facility):
                    matching_spaces.append(space)

            if matching_spaces:
                print(f"✅ {len(matching_spaces)}개 공간 매칭됨")
                result = f"**🔍 '{user_input}' 검색 결과**\n\n"

                for i, space in enumerate(matching_spaces[:5], 1):  # 최대 5개만 표시
                    result += f"**{i}.** "
                    result += self.format_space_detail(space)
                    result += "\n"

                if len(matching_spaces) > 5:
                    result += f"... 외 {len(matching_spaces) - 5}개 공간 더 있음\n"

                return result

            # 특정 공간명이 없는 경우 - 전체 공간 목록 표시
            return self.show_all_spaces_detail()

        except Exception as e:
            print(f"❌ 청년 공간 상세 처리 오류: {e}")
            return "청년 공간 상세 정보를 불러오는 중 오류가 발생했습니다."

    def show_all_spaces_detail(self):
        """모든 청년 공간을 상세 포맷으로 표시"""
        try:
            result = "**🏢 부산 청년 공간 상세 정보**\n\n"
            result += "아래 공간들 중 원하는 공간명을 입력하시면 더 자세한 정보를 확인할 수 있습니다!\n\n"

            # 지역별로 그룹화
            regions = {}
            for space in self.spaces_data:
                location = space.get('location', '기타')
                if location not in regions:
                    regions[location] = []
                regions[location].append(space)

            # 지역별로 표시 (최대 3개 지역만)
            count = 0
            for region, spaces in list(regions.items())[:3]:
                result += f"**📍 {region}**\n"

                # 각 지역의 공간들 (최대 2개만)
                for space in spaces[:2]:
                    result += self.format_space_detail(space)
                    result += "\n"

                if len(spaces) > 2:
                    result += f"... 외 {len(spaces) - 2}개 공간 더 있음\n\n"
                else:
                    result += "\n"

                count += 1
                if count >= 3:
                    break

            # 더 많은 공간이 있는 경우
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

        except Exception as e:
            print(f"❌ 전체 공간 상세 표시 오류: {e}")
            return "청년 공간 목록을 불러오는 중 오류가 발생했습니다."

    def search_spaces_by_keyword_json(self, keyword):
        """JSON 데이터에서 키워드로 공간 검색 - 새로운 키워드 형태에 맞게 수정"""
        try:
            print(f"🔍 키워드 검색 시작: '{keyword}'")
            print(f"📊 로드된 데이터 개수: {len(self.spaces_data)}")

            if not self.spaces_data:
                return f"❌ 청년 공간 데이터를 불러올 수 없습니다."

            # 새로운 키워드 매핑 (프론트엔드 버튼과 정확히 일치)
            keyword_mapping = {
                "📝스터디/회의": ["📝스터디/회의", "📝 스터디/회의", "스터디/회의", "스터디", "회의"],
                "🎤교육/강연": ["🎤교육/강연", "🏫교육/강연", "🏫 교육/강연", "교육/강연", "교육", "강연"],
                "👥커뮤니티": ["👥커뮤니티", "👥모임/커뮤니티", "👥 모임/커뮤니티", "모임/커뮤니티", "커뮤니티", "모임"],
                "🚀진로/창업": ["🚀진로/창업", "🚀 진로/창업", "진로/창업", "진로", "창업"],
                "🎨문화/창작": ["🎨문화/창작", "🎨 문화/창작", "문화/창작", "문화", "창작"],
                "🛠작업/창작실": ["🛠작업/창작실", "💻작업/창작실", "💻 작업/창작실", "작업/창작실", "작업", "창작실"],
                "🧘휴식/놀이": ["🧘휴식/놀이", "🌿휴식/놀이", "🌿 휴식/놀이", "휴식/놀이", "휴식", "놀이"],
                "🎪행사/이벤트": ["🎪행사/이벤트", "🎬행사/이벤트", "🎬 행사/이벤트", "행사/이벤트", "행사", "이벤트"]
            }

            # 검색할 키워드 목록 생성
            search_keywords = keyword_mapping.get(keyword, [keyword])
            print(f"🎯 검색 키워드 목록: {search_keywords}")

            filtered_spaces = []
            for space in self.spaces_data:
                # keywords 배열에서 검색
                space_keywords = space.get('keywords', [])
                print(f"🏢 공간: {space.get('space_name')} - 키워드: {space_keywords}")

                # 키워드 매칭 확인
                found_match = False
                for search_kw in search_keywords:
                    for space_kw in space_keywords:
                        if search_kw.lower() in space_kw.lower() or space_kw.lower() in search_kw.lower():
                            found_match = True
                            print(f"✅ 매칭 발견: '{search_kw}' <-> '{space_kw}'")
                            break
                    if found_match:
                        break

                if found_match:
                    filtered_spaces.append(space)

            print(f"📋 검색 결과: {len(filtered_spaces)}개 공간")

            if not filtered_spaces:
                return f"**{keyword}** 관련 청년공간을 찾을 수 없습니다.\n\n다른 키워드로 검색해보세요!\n\n💡 **사용 가능한 키워드:**\n- 📝스터디/회의\n- 🎤교육/강연\n- 👥커뮤니티\n- 🚀진로/창업\n- 🎨문화/창작\n- 🛠작업/창작실\n- 🧘휴식/놀이\n- 🎪행사/이벤트"

            # 결과 포맷팅 - parent_facility - space_name [location] 형태
            result = f"**{keyword}**로 찾은 공간입니다!\n\n"

            # 모든 매칭된 공간을 표시 (개수 제한 없음)
            for i, space in enumerate(filtered_spaces, 1):
                parent_facility = space.get('parent_facility', '정보없음')
                space_name = space.get('space_name', '정보없음')
                location = space.get('location', '정보없음')

                result += f"**{i}.** {parent_facility} - {space_name} [{location}]\n"

            # 마지막 안내 메시지
            result += "\n📌 **공간 상세 내용은**\n"
            result += "👉 \"청년 공간 상세\" 버튼을 눌러 확인하거나,\n"
            result += "👉 공간명을 입력해서 직접 확인해보세요!"

            return result

        except Exception as e:
            print(f"❌ 키워드 검색 오류: {e}")
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

    def handle_space_reservation_search(self, conditions):
        """조건별 청년 공간 검색 - JSON 데이터 기반"""
        try:
            region = conditions.get('region', '').strip()
            capacity = conditions.get('capacity', '').strip()
            purpose = conditions.get('purpose', '').strip()

            print(f"🔍 검색 조건: 지역={region}, 인원={capacity}, 목적={purpose}")

            if not any([region, capacity, purpose]):
                return "❌ 지역, 인원, 이용 목적 중 하나는 반드시 선택해주세요."

            # 조건 표시
            condition_display = []
            if region: condition_display.append(f"지역 : {region}")
            if capacity: condition_display.append(f"인원 : {capacity}")
            if purpose: condition_display.append(f"목적 : {purpose}")

            # spaces_busan_youth.json 데이터에서 검색
            filtered_spaces = []

            for space in self.spaces_data:
                match_score = 0
                match_reasons = []

                # 1. 지역 조건 확인
                if region and space.get('location') == region:
                    match_score += 1
                    match_reasons.append(f"지역: {region}")

                # 2. 인원 조건 확인
                if capacity and self.check_capacity_match(space, capacity):
                    match_score += 1
                    match_reasons.append(f"인원: {capacity}")

                # 3. 목적 조건 확인
                if purpose and self.check_purpose_match(space, purpose):
                    match_score += 1
                    match_reasons.append(f"목적: {purpose}")

                # 조건을 만족하는 경우에만 추가
                if match_score > 0:
                    space_copy = space.copy()
                    space_copy['match_score'] = match_score
                    space_copy['match_reasons'] = match_reasons
                    filtered_spaces.append(space_copy)

            print(f"📊 검색 결과: {len(filtered_spaces)}개 공간 발견")

            if not filtered_spaces:
                return self.format_no_results_message(region, capacity, purpose)

            # 검색 결과 포맷팅 (사용자가 제시한 형식으로)
            result = f"✅ **선택하신 조건**\n"
            for condition in condition_display:
                result += f"• {condition}\n"
            result += f"\n🔎 **조건에 맞는 공간을 찾고 있어요...**\n\n"

            return self.format_search_results(filtered_spaces, region, capacity, purpose)

        except Exception as e:
            print(f"❌ 검색 처리 오류: {e}")
            return "검색 중 오류가 발생했습니다. 다시 시도해주세요."

    def check_capacity_match(self, space, selected_capacity):
        """인원 조건 매칭 확인"""
        try:
            capacity_min = space.get('capacity_min')
            capacity_max = space.get('capacity_max')

            # 용량 정보가 없으면 모든 조건에 매칭
            if not capacity_min and not capacity_max:
                return True

            # 선택된 조건에 따른 매칭
            if selected_capacity == '1-2명':
                if capacity_min is None or capacity_min <= 2:
                    return True
            elif selected_capacity == '3-6명':
                if (capacity_min is None or capacity_min <= 6) and (capacity_max is None or capacity_max >= 3):
                    return True
            elif selected_capacity == '7명이상':
                if capacity_max is None or capacity_max >= 7:
                    return True
            elif selected_capacity == '상관없음':
                return True

            return False
        except Exception as e:
            print(f"인원 매칭 오류: {e}")
            return True  # 오류 시 매칭으로 처리

    def check_purpose_match(self, space, selected_purpose):
        """목적 조건 매칭 확인"""
        try:
            space_keywords = space.get('keywords', [])
            if not space_keywords:
                return False

            # 목적별 키워드 매핑
            purpose_mapping = {
                '스터디/회의': ['📝스터디/회의', '📝 스터디/회의', '스터디', '회의'],
                '교육/강연': ['🎤교육/강연', '🏫교육/강연', '🏫 교육/강연', '교육', '강연'],
                '커뮤니티': ['👥커뮤니티', '👥모임/커뮤니티', '👥 모임/커뮤니티', '커뮤니티', '모임'],
                '진로/창업': ['🚀진로/창업', '🚀 진로/창업', '진로', '창업'],
                '문화/창작': ['🎨문화/창작', '🎨 문화/창작', '문화', '창작'],
                '작업/창작실': ['🛠작업/창작실', '💻작업/창작실', '💻 작업/창작실', '작업', '창작실'],
                '휴식/놀이': ['🧘휴식/놀이', '🌿휴식/놀이', '🌿 휴식/놀이', '휴식', '놀이'],
                '행사/이벤트': ['🎪행사/이벤트', '🎬행사/이벤트', '🎬 행사/이벤트', '행사', '이벤트']
            }

            search_keywords = purpose_mapping.get(selected_purpose, [selected_purpose])

            for search_kw in search_keywords:
                for space_kw in space_keywords:
                    if search_kw.lower() in space_kw.lower() or space_kw.lower() in search_kw.lower():
                        return True

            return False
        except Exception as e:
            print(f"목적 매칭 오류: {e}")
            return False

    def format_search_results(self, spaces, region, capacity, purpose):
        """검색 결과 포맷팅 - 사용자가 제시한 형식으로"""
        try:
            # 매칭 점수 순으로 정렬
            spaces.sort(key=lambda x: x.get('match_score', 0), reverse=True)

            result = f"📌 **총 {len(spaces)}개의 공간**을 찾았어요!\n\n"
            result += "---\n\n"

            for i, space in enumerate(spaces, 1):
                result += f"**{i}️⃣ {space.get('parent_facility', '정보없음')} – {space.get('space_name', '정보없음')}**\n"
                result += f"{space.get('introduction', '정보없음')}\n"
                result += f"• 📍 **위치 :** {space.get('location', '정보없음')}\n"

                # 인원 정보 포맷팅
                capacity_info = self.format_capacity_info(space)
                result += f"• 👥 **인원 :** {capacity_info}\n"

                result += f"• **지원 대상 :** {space.get('eligibility', '정보없음')}\n"
                result += f"• 🧰 **특징 :** {space.get('features', '정보없음')}\n"

                # 링크 처리
                link = space.get('link')
                if isinstance(link, list) and len(link) > 0:
                    link_url = link[0]
                elif isinstance(link, str):
                    link_url = link
                else:
                    link_url = None

                if link_url:
                    result += f"• 🔗 **링크 :** {link_url}\n"

                result += "\n---\n\n"

            result += "다른 공간을 보고싶다면? **[✨ 랜덤 추천]**(버튼)"

            return result

        except Exception as e:
            print(f"결과 포맷팅 오류: {e}")
            return "검색 결과를 표시하는 중 오류가 발생했습니다."

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

            import random
            random_space = random.choice(self.spaces_data)

            result = "🎲 **랜덤으로 추천해드릴게요!**\n\n"
            result += f"**1️⃣ {random_space.get('parent_facility', '정보없음')} – {random_space.get('space_name', '정보없음')}**\n"
            result += f"{random_space.get('introduction', '정보없음')}\n"
            result += f"• 📍 **위치 :** {random_space.get('location', '정보없음')}\n"

            capacity_info = self.format_capacity_info(random_space)
            result += f"• 👥 **인원 :** {capacity_info}\n"

            result += f"• **지원 대상 :** {random_space.get('eligibility', '정보없음')}\n"
            result += f"• 🧰 **특징 :** {random_space.get('features', '정보없음')}\n"

            # 링크 처리
            link = random_space.get('link')
            if isinstance(link, list) and len(link) > 0:
                link_url = link[0]
            elif isinstance(link, str):
                link_url = link
            else:
                link_url = None

            if link_url:
                result += f"• 🔗 **링크 :** {link_url}\n"

            result += "\n💡 다른 공간이 궁금하시면 다시 랜덤 추천을 눌러보세요!"

            return result

        except Exception as e:
            print(f"랜덤 추천 오류: {e}")
            return "랜덤 추천 중 오류가 발생했습니다."

    def generate_bot_response(self, user_message_text, chat_id):
        """봇 응답 생성 로직"""

        print(f"🤖 봇 응답 생성 시작: '{user_message_text}'")

        # 0. 청년 공간 상세 처리
        if user_message_text == "청년 공간 상세":
            print(f"🏢 청년 공간 상세 버튼 클릭 감지")
            return "[SPACE_DETAIL_SEARCH]"

        # 1. 조건별 검색 요청 처리 (청년공간만)
        if "조건별 검색:" in user_message_text:
            print(f"🔍 조건별 검색 감지: '{user_message_text}'")
            try:
                search_part = user_message_text.split("조건별 검색:", 1)[1].strip()
                conditions = {}

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

                print(f"🎯 검색 조건: {conditions}")
                return self.handle_space_reservation_search(conditions)

            except Exception as e:
                print(f"❌ 조건별 검색 파싱 오류: {e}")
                return f"검색 조건 처리 중 오류가 발생했습니다: {str(e)}"

        # 2. 랜덤 추천 처리
        if user_message_text == "✨ 랜덤 추천":
            print(f"🎲 랜덤 추천 요청")
            return self.handle_random_recommendation()

        # 3. "지역 프로그램" 형태 메시지 처리 (기존 로직 유지)
        if " 프로그램" in user_message_text:
            region = user_message_text.replace(" 프로그램", "").strip()
            regions = ['중구', '동구', '서구', '영도구', '부산진구', '동래구', '연제구',
                       '금정구', '북구', '사상구', '사하구', '강서구', '남구', '해운대구', '수영구', '기장군']

            if region in regions:
                return search_programs_by_region(region)

        # 4. 지역별 검색 처리 (청년공간만)
        regions = ['중구', '동구', '서구', '영도구', '부산진구', '동래구', '연제구',
                   '금정구', '북구', '사상구', '사하구', '강서구', '남구', '해운대구', '수영구', '기장군']

        for region in regions:
            if user_message_text.strip() == region:
                # 항상 청년공간만 검색 (프로그램 맥락 체크 제거)
                return search_spaces_by_region(region)

        # 5. 새로운 키워드 검색 처리 (JSON 데이터 사용)
        keyword_list = [
            '📝스터디/회의',
            '🎤교육/강연',
            '👥커뮤니티',
            '🚀진로/창업',
            '🎨문화/창작',
            '🛠작업/창작실',
            '🧘휴식/놀이',
            '🎪행사/이벤트'
        ]

        for keyword in keyword_list:
            if user_message_text.strip() == keyword:
                print(f"🎯 새로운 키워드 매칭: '{keyword}'")
                return self.search_spaces_by_keyword_json(keyword)

        # 6. 구버전 키워드와의 호환성 처리
        old_keyword_mapping = {
            '스터디/회의': '📝스터디/회의',
            '교육/강연': '🎤교육/강연',
            '모임/커뮤니티': '👥커뮤니티',
            '진로/창업': '🚀진로/창업',
            '문화/창작': '🎨문화/창작',
            '작업/창작실': '🛠작업/창작실',
            '휴식/놀이': '🧘휴식/놀이',
            '행사/이벤트': '🎪행사/이벤트'
        }

        for old_keyword, new_keyword in old_keyword_mapping.items():
            if user_message_text.strip() == old_keyword:
                print(f"🔄 구버전 키워드 호환: '{old_keyword}' -> '{new_keyword}'")
                return self.search_spaces_by_keyword_json(new_keyword)

        # 7. 프로그램 관련 키워드 검색
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

        # 8. 기타 키워드 검색 처리 (기존 크롤링 데이터 사용)
        if any(keyword in user_message_text for keyword in ['스터디', '창업', '회의', '카페', '라운지', '센터']):
            return search_spaces_by_keyword(user_message_text)

        # 9. OpenAI 호출
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

        except Exception as e:
            print(f"OpenAI API 오류: {e}")
            return "죄송합니다, 답변 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."


# 전역 인스턴스 생성
chat_handler = ChatHandler()
