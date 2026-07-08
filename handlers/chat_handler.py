import os
import json
import openai
import random
from datetime import datetime

from database.models import db, User, Chat, Message
from config.predefined_answers import PREDEFINED_ANSWERS
from services.youth_space_crawler import search_spaces_by_region, search_spaces_by_keyword
from services.youth_program_crawler import get_youth_programs_data, search_programs_by_region
from handlers.base_handler import BaseHandler


class ChatHandler(BaseHandler):
    def __init__(self):
        print("🚀 ChatHandler 초기화 시작...")

        try:
            self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception as e:
            self.client = None

        self.spaces_data = self.load_spaces_data()
        self.centers_data = self.load_centers_data()
        self.keyword_data = self.load_keyword_data()
        self.keyword_mapping = self._init_keyword_mapping()
        self.purpose_mapping = self._init_purpose_mapping()

        if len(self.centers_data) == 0:
            import time
            time.sleep(1)
            self.centers_data = self.load_centers_data()

        if self.centers_data:
            sample_center = self.centers_data[0]

        if self.spaces_data:
            sample_space = self.spaces_data[0]


    def load_centers_data(self):
        """youth_spaces_cache.json 데이터 로드 - config 폴더에서만"""
        try:
            config_path = self.get_config_path()
            config_file = os.path.join(config_path, 'youth_spaces_cache.json')

            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    result = data.get('data', [])
                    return result

            return []

        except Exception as e:
            return []

    def load_keyword_data(self):
        """spaces_busan_keyword.json 데이터 로드"""
        try:
            config_path = self.get_config_path()
            keyword_file = os.path.join(config_path, 'spaces_busan_keyword.json')

            if os.path.exists(keyword_file):
                with open(keyword_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    result = data.get('spaces_busan_keyword', [])
                    return result

            return []
        except Exception as e:
            return []

    def load_overrides_data(self):
        """youth_spaces_overrides.json 데이터 로드 - config 폴더에서"""
        try:
            config_path = self.get_config_path()
            overrides_file = os.path.join(config_path, 'youth_spaces_overrides.json')

            if os.path.exists(overrides_file):
                with open(overrides_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('data', [])
            return []
        except Exception:
            return []

    def merge_centers_data(self):
        """크롤링 데이터와 Override 데이터 병합 (name + region으로 구분)"""
        try:
            cache_centers = self.centers_data.copy()
            override_centers = self.load_overrides_data()

            override_dict = {}
            for center in override_centers:
                key = f"{center.get('name', '')}_{center.get('region', '')}"
                override_dict[key] = center

            merged_centers = []

            for cache_center in cache_centers:
                center_name = cache_center.get('name', '')
                center_region = cache_center.get('region', '')
                key = f"{center_name}_{center_region}"

                if key in override_dict:
                    merged_centers.append(override_dict[key])
                else:
                    merged_centers.append(cache_center)

            cache_keys = {f"{center.get('name', '')}_{center.get('region', '')}" for center in cache_centers}
            for override_center in override_centers:
                override_key = f"{override_center.get('name', '')}_{override_center.get('region', '')}"
                if override_key not in cache_keys:
                    merged_centers.append(override_center)

            return merged_centers

        except Exception:
            return self.centers_data

    def merge_center_data(self, center_name):
        """특정 센터의 크롤링 데이터 + Override 데이터 + 키워드 데이터 병합"""
        try:
            merged_centers = self.merge_centers_data()
            center_info = None

            for center in merged_centers:
                if center.get('name') == center_name:
                    center_info = center.copy()
                    break

            if not center_info:
                return None

            for keyword_item in self.keyword_data:
                if keyword_item.get('parent_facility') == center_name:
                    center_info['introduction'] = keyword_item.get('introduction', '')
                    center_info['keywords'] = keyword_item.get('keywords', [])
                    break

            return center_info

        except Exception:
            return None

    def get_all_centers_cards(self):
        """33개 센터 카드형 데이터 반환 (Override 적용)"""
        try:
            result = "[CENTER_LIST_VIEW]"
            return result
        except Exception:
            return "33개 센터 정보를 불러오는 중 오류가 발생했습니다."

    def get_center_detail_with_spaces(self, center_name):
        """특정 센터 상세 정보 + 대여가능한 공간들 반환 (Override 적용)"""
        try:
            center_info = self.merge_center_data(center_name)
            if not center_info:
                return f"'{center_name}' 센터 정보를 찾을 수 없습니다."

            result = f"{center_info.get('name', '')}[{center_info.get('region', '')}]\n"

            if center_info.get('introduction'):
                result += f"{center_info['introduction']}\n\n"

            if center_info.get('address'):
                result += f"📍 {center_info['address']}\n"
            if center_info.get('contact'):
                result += f"📞 {center_info['contact']}\n"
            if center_info.get('hours'):
                result += f"🕒 {center_info['hours']}\n"
            if center_info.get('description'):
                result += f"📝 {center_info['description']}\n"

            links = []
            if center_info.get('homepage'):
                links.append(f"[홈페이지]({center_info['homepage']})")
            if center_info.get('rental_link'):
                links.append(f"[대관신청]({center_info['rental_link']})")
            if center_info.get('program_link'):
                links.append(f"[프로그램]({center_info['program_link']})")
            if center_info.get('sns'):
                links.append(f"[SNS]({center_info['sns']})")

            if links:
                result += f"🔗 {' | '.join(links)}\n"

            if center_info.get('keywords'):
                keywords_str = ', '.join(center_info['keywords'])
                result += f"🏷️ 사용 가능한 키워드: {keywords_str}\n\n"

            rental_spaces = []
            for space in self.spaces_data:
                if space.get('parent_facility') == center_name:
                    rental_spaces.append(space)

            if rental_spaces:
                result += f"[CENTER_RENTAL_SPACES:{center_name}]"
            else:
                result += "현재 이 센터에는 대여 가능한 공간 정보가 없습니다."

            return result

        except Exception:
            return f"'{center_name}' 센터 정보를 처리하는 중 오류가 발생했습니다."

    def get_space_detail_by_facility_and_name(self, facility_name, space_name):
        """센터명과 공간명으로 특정 공간 상세 정보 반환"""
        try:
            target_space = None
            for space in self.spaces_data:
                if (space.get('parent_facility') == facility_name and
                        space.get('space_name') == space_name):
                    target_space = space
                    break

            if not target_space:
                return f"'{facility_name}'의 '{space_name}' 공간을 찾을 수 없습니다."

            result = f"🏢 {target_space.get('parent_facility', '정보없음')} - {target_space.get('space_name', '정보없음')}\n\n"

            if target_space.get('introduction'):
                result += f"{target_space['introduction']}\n\n"

            result += f"\u00A0\u00A0📍 위치 : {target_space.get('location', '정보없음')}\n"

            capacity_info = self.format_capacity_info(target_space)
            result += f"\u00A0\u00A0👥 인원 : {capacity_info}\n"

            if target_space.get('eligibility'):
                result += f"\u00A0\u00A0🎯 지원 대상 : {target_space['eligibility']}\n"

            if target_space.get('features'):
                result += f"\u00A0\u00A0🧰 특징 : {target_space['features']}\n"

            link_url = self.extract_link_url(target_space.get('link'))
            if link_url != '정보없음':
                result += f"\u00A0\u00A0🔗 링크 : [자세히 보기]({link_url})\n"

            if target_space.get('keywords'):
                result += f"\u00A0\u00A0🏷️ 사용 가능한 키워드 : {', '.join(target_space['keywords'])}\n"

            return result

        except Exception:
            return f"'{facility_name}'의 '{space_name}' 공간 정보를 처리하는 중 오류가 발생했습니다."

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

    def format_space_detail(self, space):
        """청년 공간 상세 정보 포맷팅 - 정형화된 형식"""
        try:
            parent_facility = space.get('parent_facility', '정보없음')
            space_name = space.get('space_name', '정보없음')
            location = space.get('location', '정보없음')
            introduction = space.get('introduction', '정보없음')
            eligibility = space.get('eligibility', '정보없음')
            features = space.get('features', '정보없음')

            capacity_info = self.format_capacity_info(space)
            link_url = self.extract_link_url(space.get('link'))

            result = f"🏢 {parent_facility} - {space_name}\n\n"
            result += f"{introduction}\n"

            result += f"\u00A0\u00A0📍 위치 : "
            result += f"{location}\n"

            result += f"\u00A0\u00A0👥 인원 : "
            result += f"{capacity_info}\n"

            result += f"\u00A0\u00A0🎯 지원 대상 : "
            result += f"{eligibility}\n"

            result += f"\u00A0\u00A0🧰 특징 : "
            result += f"{features}\n"

            if link_url != '정보없음':
                result += f"\u00A0\u00A0🔗 링크 : "
                result += f"[자세히 보기]({link_url})\n"

            if space.get('keywords'):
                result += f"\u00A0\u00A0🏷️ 사용 가능한 키워드 : "
                result += f"{', '.join(space.get('keywords'))}\n"

            return result

        except Exception:
            return "공간 정보를 불러오는 중 오류가 발생했습니다."

    def load_spaces_data(self):
        """spaces_busan_youth.json 데이터 로드"""
        try:
            config_path = self.get_config_path()
            spaces_file = os.path.join(config_path, 'spaces_busan_youth.json')

            if os.path.exists(spaces_file):
                with open(spaces_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    result = data.get('spaces_busan_youth', [])
                    return result

            return []

        except Exception as e:
            return []

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
                matching_spaces.sort(key=lambda x: x.get('parent_facility', ''))
                result = f"**🔍 '{user_input}' 검색 결과**\n\n"

                for i, space in enumerate(matching_spaces[:5], 1):
                    result += f"**{i}.\u00A0.** "
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
            result = "**🏢 부산 청년 공간**\n\n"
            result += "아래 공간들 중 원하는 공간명을 입력하시면 더 자세한 정보를 확인할 수 있습니다!\n\n"

            regions = {}
            for space in self.spaces_data:
                location = space.get('location', '기타')
                regions.setdefault(location, []).append(space)

            for region in regions:
                regions[region].sort(key=lambda x: x.get('parent_facility', ''))

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

            result += f"💡 총 **{total_spaces}\u00A0개**의 청년 공간이 있습니다.\n"
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
                return (f"{keyword}로 검색할 수 있는 공간을 찾아보겠습니다.\n\n"
                        f"💡사용 가능한 키워드 : \n"
                        f"📝스터디/회의\n- 🎤교육/강연\n- 👥커뮤니티\n- 🚀진로/창업\n- 🎨문화/창작\n- 🛠작업/창작실\n- 🧘휴식/놀이\n- 🎪행사/이벤트")

            filtered_spaces.sort(key=lambda x: x.get('parent_facility', ''))
            result = f"{keyword}(으)로 찾은 공간입니다!\n\n"

            for i, space in enumerate(filtered_spaces, 1):
                parent_facility = space.get('parent_facility', '정보없음')
                space_name = space.get('space_name', '정보없음')
                location = space.get('location', '정보없음')
                result += f"{i}\\.\u00A0{parent_facility} - {space_name} [{location}]\n"

            result += "\n**📌\u00A0공간 상세 내용은**"
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

            result = f"✅ 선택하신 조건\n"
            for condition in condition_display:
                result += f"\u00A0\u00A0{condition}\n"
            result += f"\n🔎 조건에 맞는 공간을 찾고 있어요...\n\n"

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
        """검색 결과 포맷팅 - 버튼 추가"""
        try:
            spaces.sort(key=lambda x: (-x.get('match_score', 0), x.get('parent_facility', '')))

            result = f"📌\u00A0총\u00A0{len(spaces)}개의 공간을 찾았어요!\n\n"

            for i, space in enumerate(spaces, 1):
                result += f"{i}.\u00A0{space.get('parent_facility', '정보없음')} – {space.get('space_name', '정보없음')}\n"
                result += f"{space.get('introduction', '정보없음')}\n"
                result += f"\u00A0\u00A0📍 위치 : {space.get('location', '정보없음')}\n"
                result += f"\u00A0\u00A0👥 인원 : {self.format_capacity_info(space)}\n"
                result += f"\u00A0\u00A0🎯 지원 대상 : {space.get('eligibility', '정보없음')}\n"
                result += f"\u00A0\u00A0🧰 특징 : {space.get('features', '정보없음')}\n"

                link_url = self.extract_link_url(space.get('link'))
                if link_url and link_url != '정보없음':
                    result += f"\u00A0\u00A0🔗 링크 : [자세히 보기]({link_url})\n"

                result += "---\n"

            result += "[SHOW_CONDITIONAL_SEARCH_BUTTONS]"

            return result

        except Exception:
            return "검색 결과를 표시하는 중 오류가 발생했습니다."

    def format_no_results_message(self, region, capacity, purpose):
        """결과 없음 메시지 포맷팅 - 버튼 추가"""
        conditions = []
        if region: conditions.append(f"지역: {region}")
        if capacity: conditions.append(f"인원: {capacity}")
        if purpose: conditions.append(f"목적: {purpose}")

        condition_text = ", ".join(conditions)

        result = f"😥 {condition_text} 조건에 맞는 청년공간을 찾을 수 없습니다.\n\n"
        result += "💡 다른 조건으로 검색해보세요!\n"
        result += "\u00A0\u00A0지역 조건을 넓혀보거나\n"
        result += "\u00A0\u00A0인원 조건을 '상관없음'으로 변경하거나\n"
        result += "\u00A0\u00A0다른 이용 목적을 선택해보세요\n\n"
        result += "💡 **다른 방법으로 공간을 찾아보세요!**\n\n"
        result += "[SHOW_CONDITIONAL_SEARCH_BUTTONS]"

        return result

    def handle_random_recommendation(self):
        """랜덤 추천 처리 - 추가 버튼 포함"""
        try:
            if not self.spaces_data:
                return "추천할 청년공간 정보를 불러올 수 없습니다."

            random_space = random.choice(self.spaces_data)

            result = "**🎲\u00A0\u00A0랜덤으로 추천해드릴게요!**\n\n"
            result += f"**{random_space.get('parent_facility', '정보없음')} – {random_space.get('space_name', '정보없음')}**\n"
            result += f"{random_space.get('introduction', '정보없음')}\n"
            result += f"\u00A0\u00A0📍 위치 : {random_space.get('location', '정보없음')}\n"
            result += f"\u00A0\u00A0👥 인원 : {self.format_capacity_info(random_space)}\n"
            result += f"\u00A0\u00A0🎯 지원 대상 : {random_space.get('eligibility', '정보없음')}\n"
            result += f"\u00A0\u00A0🧰 특징 : {random_space.get('features', '정보없음')}\n"

            link_url = self.extract_link_url(random_space.get('link'))
            if link_url and link_url != '정보없음':
                result += f"\u00A0\u00A0🔗 링크 : [자세히 보기]({link_url})\n"

            result += "---"
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
                db.session.commit()

            if len(chat_session.messages) == 0 and user_message_text not in PREDEFINED_ANSWERS:
                chat_session.title = user_message_text
                db.session.commit()

            user_message = Message(chat_id=chat_id, sender='user', text=user_message_text)
            db.session.add(user_message)
            db.session.commit()

            bot_reply = self.generate_bot_response(user_message_text, chat_id)

            bot_message = Message(chat_id=chat_id, sender='bot', text=bot_reply)
            db.session.add(bot_message)
            db.session.commit()

            return {"success": True, "reply": bot_reply}, 200

        except Exception as e:
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
            "✨ 랜덤 추천": self.handle_random_recommendation(),
            "34개 센터 전체보기": self.get_all_centers_cards()
        }

        if user_message_text in special_commands:
            command_result = special_commands[user_message_text]
            result = command_result() if callable(command_result) else command_result
            return result

        if user_message_text.endswith(' 상세보기'):
            center_name = user_message_text.replace(' 상세보기', '').strip()

            merged_centers = self.merge_centers_data()
            if merged_centers:
                center_names = [center.get('name', '') for center in merged_centers[:3]]

            result = self.get_center_detail_with_spaces(center_name)
            return result

        if '-' in user_message_text and user_message_text.endswith(' 상세보기'):
            space_detail = user_message_text.replace(' 상세보기', '').strip()
            if '-' in space_detail:
                parts = space_detail.split('-', 1)
                if len(parts) == 2:
                    facility_name = parts[0].strip()
                    space_name = parts[1].strip()
                    result = self.get_space_detail_by_facility_and_name(facility_name, space_name)
                    return result

        if "조건별 검색:" in user_message_text:
            try:
                conditions = self.parse_search_conditions(user_message_text)
                result = self.handle_space_reservation_search(conditions)
                return result
            except Exception as e:
                return "검색 조건 처리 중 오류가 발생했습니다."

        if " 프로그램" in user_message_text:
            region = user_message_text.replace(" 프로그램", "").strip()
            regions = ['중구', '동구', '서구', '영도구', '부산진구', '동래구', '연제구',
                       '금정구', '북구', '사상구', '사하구', '강서구', '남구', '해운대구', '수영구', '기장군']

            if region in regions:
                result = search_programs_by_region(region)
                return result

        regions = ['중구', '동구', '서구', '영도구', '부산진구', '동래구', '연제구',
                   '금정구', '북구', '사상구', '사하구', '강서구', '남구', '해운대구', '수영구', '기장군']

        if user_message_text.strip() in regions:
            result = search_spaces_by_region(user_message_text.strip())
            return result

        keyword_list = list(self.keyword_mapping.keys())
        if user_message_text.strip() in keyword_list:
            result = self.search_spaces_by_keyword_json(user_message_text.strip())
            return result

        old_keyword_mapping = {
            '스터디/회의': '📝스터디/회의', '교육/강연': '🎤교육/강연',
            '모임/커뮤니티': '👥커뮤니티', '진로/창업': '🚀진로/창업',
            '문화/창작': '🎨문화/창작', '작업/창작실': '🛠작업/창작실',
            '휴식/놀이': '🧘휴식/놀이', '행사/이벤트': '🎪행사/이벤트'
        }

        if user_message_text.strip() in old_keyword_mapping:
            new_keyword = old_keyword_mapping[user_message_text.strip()]
            result = self.search_spaces_by_keyword_json(new_keyword)
            return result

        if any(keyword in user_message_text for keyword in ['스터디', '창업', '회의', '카페', '라운지', '센터']):
            result = search_spaces_by_keyword(user_message_text)
            if '찾을 수 없습니다' not in result:
                return result

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
            result = response.choices[0].message.content
            return result

        except Exception as e:
            return "죄송합니다, 답변 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."


chat_handler = ChatHandler()