import json
import os
from collections import Counter
from services.youth_space_crawler import (
    get_youth_spaces_data,
    search_spaces_by_region,
    search_spaces_by_keyword,
    get_all_youth_spaces
)


class SpaceHandler:
    def __init__(self):
        self.additional_info = self.load_additional_space_info()

    def load_additional_space_info(self):
        """추가 공간 정보 JSON 파일 로드"""
        try:
            basedir = os.path.abspath(os.path.dirname(__file__))
            project_root = os.path.dirname(basedir)
            config_path = os.path.join(project_root, 'config')

            additional_info_file = os.path.join(config_path, 'additional_space_info.json')

            if os.path.exists(additional_info_file):
                with open(additional_info_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('additional_space_info', {})
            else:
                print("추가 공간 정보 파일을 찾을 수 없습니다.")
                return {}
        except Exception as e:
            print(f"추가 공간 정보 로드 오류: {e}")
            return {}

    def merge_space_data(self, basic_space_data):
        """기본 크롤링 데이터와 추가 정보 통합"""
        merged_data = []

        for space in basic_space_data:
            space_name = space.get('name', '')
            merged_space = space.copy()

            # 추가 정보가 있는 경우 병합
            if space_name in self.additional_info:
                additional = self.additional_info[space_name]

                # 추가 정보 필드들 병합
                merged_space['facility_details'] = additional.get('facility_details', [])
                merged_space['target_users'] = additional.get('target_users', '')
                merged_space['keywords'] = additional.get('keywords', [])
                merged_space['notice'] = additional.get('notice', '')
                merged_space['price_info'] = self.extract_price_info(additional.get('facility_details', []))
                merged_space['equipment_summary'] = self.extract_equipment_summary(
                    additional.get('facility_details', []))

                # 추가 URL들
                if additional.get('additional_crawl_url'):
                    merged_space['additional_crawl_url'] = additional['additional_crawl_url']
                if additional.get('booking_url'):
                    merged_space['booking_url'] = additional['booking_url']
                if additional.get('rental_form'):
                    merged_space['rental_form'] = additional['rental_form']

            merged_data.append(merged_space)

        return merged_data

    def extract_price_info(self, facility_details):
        """시설별 가격 정보 추출"""
        price_info = []
        for facility in facility_details:
            if facility.get('price') and facility['price'] != "없음":
                price_info.append({
                    'facility': facility['name'],
                    'price': facility['price']
                })
        return price_info

    def extract_equipment_summary(self, facility_details):
        """시설별 장비 요약 추출"""
        equipment_set = set()
        for facility in facility_details:
            if facility.get('equipment') and facility['equipment'] != "명시되지 않음":
                # 장비를 쉼표로 분리하여 세트에 추가
                equipment_list = [eq.strip() for eq in facility['equipment'].split(',')]
                equipment_set.update(equipment_list)
        return list(equipment_set)

    def format_detailed_space_info(self, space):
        """상세 공간 정보 포맷팅"""
        result = f"**🏢 {space['name']}** [{space.get('region', '')}]\n\n"

        # 기본 정보
        if space.get('address'):
            result += f"📍 **주소**: {space['address']}\n"
        if space.get('contact'):
            result += f"📞 **연락처**: {space['contact']}\n"
        if space.get('hours'):
            result += f"🕒 **이용시간**: {space['hours']}\n"
        if space.get('description'):
            result += f"📝 **설명**: {space['description']}\n"

        # 대상 이용자
        if space.get('target_users'):
            result += f"👥 **이용대상**: {space['target_users']}\n"

        # 키워드
        if space.get('keywords'):
            result += f"🏷️ **키워드**: {', '.join(space['keywords'])}\n"

        result += "\n"

        # 시설 정보
        if space.get('facility_details'):
            result += "🏠 **시설 정보**\n"
            for i, facility in enumerate(space['facility_details'], 1):
                result += f"\n**{i}. {facility['name']}**\n"
                if facility.get('capacity'):
                    result += f"   👥 인원: {facility['capacity']}\n"
                if facility.get('type'):
                    result += f"   🏷️ 구분: {facility['type']}\n"
                if facility.get('equipment') and facility['equipment'] != "명시되지 않음":
                    result += f"   🔧 장비: {facility['equipment']}\n"
                if facility.get('price') and facility['price'] != "없음":
                    result += f"   💰 가격: {facility['price']}\n"
                if facility.get('notice') and facility['notice'] != "없음":
                    result += f"   ⚠️ 안내: {facility['notice']}\n"

        # 특별 안내사항
        if space.get('notice') and space['notice'] != "없음":
            result += f"\n⚠️ **특별 안내사항**: {space['notice']}\n"

        # 링크 정보
        links = []
        if space.get('homepage'):
            links.append(f"[홈페이지]({space['homepage']})")
        if space.get('rental_link'):
            links.append(f"[대관신청]({space['rental_link']})")
        if space.get('booking_url') and space['booking_url'] != "없음":
            links.append(f"[예약하기]({space['booking_url']})")
        if space.get('rental_form') and space['rental_form'] != "없음":
            links.append(f"[신청서]({space['rental_form']})")
        if space.get('program_link'):
            links.append(f"[프로그램]({space['program_link']})")
        if space.get('sns'):
            links.append(f"[SNS]({space['sns']})")

        if links:
            result += f"\n🔗 **관련 링크**: {' | '.join(links)}\n"

        return result

    def get_all_spaces(self):
        """전체 청년공간 목록 (추가 정보 포함)"""
        try:
            basic_spaces = get_youth_spaces_data()
            merged_spaces = self.merge_space_data(basic_spaces)

            return {
                'success': True,
                'data': merged_spaces,
                'count': len(merged_spaces),
                'message': f'{len(merged_spaces)}개의 청년공간을 찾았습니다.'
            }
        except Exception as e:
            print(f"청년공간 API 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '청년공간 정보를 가져오는 중 오류가 발생했습니다.'
            }

    def get_space_detail(self, space_name):
        """특정 공간의 상세 정보"""
        try:
            basic_spaces = get_youth_spaces_data()
            merged_spaces = self.merge_space_data(basic_spaces)

            # 공간명으로 검색
            target_space = None
            for space in merged_spaces:
                if space_name.lower() in space.get('name', '').lower():
                    target_space = space
                    break

            if not target_space:
                return {
                    'success': False,
                    'message': f'"{space_name}"와 관련된 공간을 찾을 수 없습니다.'
                }

            detailed_info = self.format_detailed_space_info(target_space)

            return {
                'success': True,
                'data': target_space,
                'message': detailed_info
            }
        except Exception as e:
            print(f"공간 상세 정보 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '공간 상세 정보를 가져오는 중 오류가 발생했습니다.'
            }

    def get_spaces_by_region(self, region):
        """지역별 청년공간 검색 (추가 정보 포함)"""
        try:
            basic_spaces = get_youth_spaces_data()
            merged_spaces = self.merge_space_data(basic_spaces)

            # 정확한 지역 매칭으로 변경
            filtered_spaces = []
            for space in merged_spaces:
                space_region = space.get('region', '').strip()
                if space_region == region:  # 정확히 일치하는 경우만
                    filtered_spaces.append(space)

            if not filtered_spaces:
                return {
                    'success': False,
                    'message': f'**{region}**에서 청년공간을 찾을 수 없습니다.\n\n다른 지역을 검색해보세요!'
                }

            # 포맷 수정: 줄바꿈 제거
            result = f"**{region} 청년공간({len(filtered_spaces)}개)**\n\n"

            for space in filtered_spaces[:5]:  # 최대 5개만 표시
                # 공간명 포맷 수정
                result += f"**{space['name']}[{space.get('region', '')}]**\n"
                if space.get('address'):
                    result += f"📍 {space['address']}\n"
                if space.get('facility_details'):
                    facility_count = len(space['facility_details'])
                    result += f"🏠 {facility_count}개 시설 보유\n"
                if space.get('target_users'):
                    result += f"👥 {space['target_users']}\n"
                if space.get('contact'):
                    result += f"📞 {space['contact']}\n"
                result += "\n"

            return {
                'success': True,
                'data': filtered_spaces,
                'count': len(filtered_spaces),
                'message': result,
                'region': region
            }
        except Exception as e:
            print(f"지역별 청년공간 API 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'{region} 지역의 청년공간 정보를 가져오는 중 오류가 발생했습니다.'
            }

    def search_spaces_by_keyword(self, keyword):
        """키워드별 청년공간 검색 (추가 정보 포함)"""
        try:
            if not keyword:
                return {
                    'success': False,
                    'error': '검색 키워드가 필요합니다.',
                    'message': '검색 키워드를 입력해주세요.'
                }

            basic_spaces = get_youth_spaces_data()
            merged_spaces = self.merge_space_data(basic_spaces)

            # 키워드로 필터링 (기본 정보 + 추가 정보에서 검색)
            filtered_spaces = []
            keyword_lower = keyword.lower()

            for space in merged_spaces:
                # 기본 검색 대상
                searchable_text = [
                    space.get('name', ''),
                    space.get('description', ''),
                    space.get('region', ''),
                    space.get('target_users', ''),
                    space.get('notice', '')
                ]

                # 키워드 배열에서도 검색
                if space.get('keywords'):
                    searchable_text.extend(space['keywords'])

                # 시설 정보에서도 검색
                if space.get('facility_details'):
                    for facility in space['facility_details']:
                        searchable_text.extend([
                            facility.get('name', ''),
                            facility.get('type', ''),
                            facility.get('equipment', ''),
                            facility.get('notice', '')
                        ])

                # 키워드 매칭 확인
                if any(keyword_lower in text.lower() for text in searchable_text):
                    filtered_spaces.append(space)

            if not filtered_spaces:
                return {
                    'success': False,
                    'message': f"**{keyword}** 관련 청년공간을 찾을 수 없습니다.\n\n다른 키워드로 검색해보세요!"
                }

            result = f"🔍 **{keyword}** 검색 결과 ({len(filtered_spaces)}개)\n\n"

            for space in filtered_spaces[:5]:  # 최대 5개만 표시
                result += f"**{space['name']}** [{space.get('region', '')}]\n"
                if space.get('address'):
                    result += f"📍 {space['address']}\n"
                if space.get('description'):
                    desc = space['description'][:100] + "..." if len(space['description']) > 100 else space[
                        'description']
                    result += f"📝 {desc}\n"

                # 키워드 표시
                if space.get('keywords'):
                    keywords_text = ', '.join(space['keywords'][:3])  # 최대 3개 키워드만
                    result += f"🏷️ {keywords_text}\n"

                # 매칭된 시설 정보 표시
                if space.get('facility_details'):
                    matching_facilities = []
                    for facility in space['facility_details']:
                        facility_text = f"{facility.get('name', '')} {facility.get('type', '')} {facility.get('equipment', '')}"
                        if keyword_lower in facility_text.lower():
                            matching_facilities.append(facility['name'])

                    if matching_facilities:
                        result += f"🏠 관련 시설: {', '.join(matching_facilities)}\n"

                result += "\n"

            return {
                'success': True,
                'data': filtered_spaces,
                'count': len(filtered_spaces),
                'message': result,
                'keyword': keyword
            }
        except Exception as e:
            print(f"키워드 검색 API 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '청년공간 검색 중 오류가 발생했습니다.'
            }

    def search_by_facility_type(self, facility_type):
        """시설 유형별 검색"""
        try:
            basic_spaces = get_youth_spaces_data()
            merged_spaces = self.merge_space_data(basic_spaces)

            filtered_spaces = []
            facility_type_lower = facility_type.lower()

            for space in merged_spaces:
                if space.get('facility_details'):
                    for facility in space['facility_details']:
                        if facility_type_lower in facility.get('type', '').lower():
                            if space not in filtered_spaces:
                                filtered_spaces.append(space)
                            break

            if not filtered_spaces:
                return {
                    'success': False,
                    'message': f"**{facility_type}** 시설을 보유한 청년공간을 찾을 수 없습니다."
                }

            result = f"🏠 **{facility_type}** 시설 보유 공간 ({len(filtered_spaces)}개)\n\n"

            for space in filtered_spaces:
                result += f"**{space['name']}** [{space.get('region', '')}]\n"

                # 해당 시설 유형의 상세 정보
                matching_facilities = []
                for facility in space.get('facility_details', []):
                    if facility_type_lower in facility.get('type', '').lower():
                        facility_info = facility['name']
                        if facility.get('capacity'):
                            facility_info += f" (정원: {facility['capacity']})"
                        matching_facilities.append(facility_info)

                if matching_facilities:
                    result += f"🏠 {', '.join(matching_facilities)}\n"

                if space.get('contact'):
                    result += f"📞 {space['contact']}\n"
                result += "\n"

            return {
                'success': True,
                'data': filtered_spaces,
                'count': len(filtered_spaces),
                'message': result,
                'facility_type': facility_type
            }
        except Exception as e:
            print(f"시설 유형별 검색 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '시설 유형별 검색 중 오류가 발생했습니다.'
            }

    def search_by_price_range(self, price_type="free"):
        """가격대별 공간 검색"""
        try:
            basic_spaces = get_youth_spaces_data()
            merged_spaces = self.merge_space_data(basic_spaces)

            filtered_spaces = []

            for space in merged_spaces:
                has_matching_price = False

                if space.get('facility_details'):
                    for facility in space['facility_details']:
                        price = facility.get('price', '없음').lower()

                        if price_type == "free" and ("무료" in price or "없음" in price):
                            has_matching_price = True
                            break
                        elif price_type == "paid" and ("원" in price and "무료" not in price and "없음" not in price):
                            has_matching_price = True
                            break

                if has_matching_price:
                    filtered_spaces.append(space)

            price_label = "무료" if price_type == "free" else "유료"

            if not filtered_spaces:
                return {
                    'success': False,
                    'message': f"**{price_label}** 이용 가능한 청년공간을 찾을 수 없습니다."
                }

            result = f"💰 **{price_label} 이용 가능한 공간** ({len(filtered_spaces)}개)\n\n"

            for space in filtered_spaces[:8]:  # 최대 8개까지 표시
                result += f"**{space['name']}** [{space.get('region', '')}]\n"

                # 해당 가격대의 시설 정보만 표시
                matching_facilities = []
                for facility in space.get('facility_details', []):
                    price = facility.get('price', '없음').lower()

                    if ((price_type == "free" and ("무료" in price or "없음" in price)) or
                            (price_type == "paid" and ("원" in price and "무료" not in price and "없음" not in price))):

                        facility_info = f"{facility['name']}"
                        if facility.get('capacity'):
                            facility_info += f" (정원: {facility['capacity']})"
                        if price_type == "paid" and "원" in price:
                            facility_info += f" - {facility['price']}"
                        matching_facilities.append(facility_info)

                if matching_facilities:
                    result += f"🏠 {', '.join(matching_facilities[:2])}\n"  # 최대 2개 시설만

                if space.get('contact'):
                    result += f"📞 {space['contact']}\n"
                result += "\n"

            return {
                'success': True,
                'data': filtered_spaces,
                'count': len(filtered_spaces),
                'message': result,
                'price_type': price_type
            }
        except Exception as e:
            print(f"가격대별 검색 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '가격대별 검색 중 오류가 발생했습니다.'
            }

    def search_by_keywords_list(self, keywords_list):
        """여러 키워드로 검색"""
        try:
            basic_spaces = get_youth_spaces_data()
            merged_spaces = self.merge_space_data(basic_spaces)

            # 키워드별 점수 계산
            scored_spaces = []

            for space in merged_spaces:
                score = 0
                matched_keywords = []

                # 검색 대상 텍스트 수집
                searchable_text = [
                    space.get('name', ''),
                    space.get('description', ''),
                    space.get('target_users', ''),
                    space.get('notice', '')
                ]

                if space.get('keywords'):
                    searchable_text.extend(space['keywords'])

                if space.get('facility_details'):
                    for facility in space['facility_details']:
                        searchable_text.extend([
                            facility.get('name', ''),
                            facility.get('type', ''),
                            facility.get('equipment', ''),
                            facility.get('notice', '')
                        ])

                # 키워드 매칭 점수 계산
                for keyword in keywords_list:
                    keyword_lower = keyword.lower()
                    for text in searchable_text:
                        if keyword_lower in text.lower():
                            score += 1
                            if keyword not in matched_keywords:
                                matched_keywords.append(keyword)
                            break

                if score > 0:
                    scored_spaces.append((space, score, matched_keywords))

            # 점수순으로 정렬
            scored_spaces.sort(key=lambda x: x[1], reverse=True)

            if not scored_spaces:
                return {
                    'success': False,
                    'message': f"**{', '.join(keywords_list)}** 관련 청년공간을 찾을 수 없습니다."
                }

            result = f"🔍 **{', '.join(keywords_list)}** 복합 검색 결과 ({len(scored_spaces)}개)\n\n"

            for space, score, matched_keywords in scored_spaces[:5]:
                result += f"**{space['name']}** [{space.get('region', '')}] ⭐{score}점\n"
                result += f"🎯 매칭 키워드: {', '.join(matched_keywords)}\n"

                if space.get('address'):
                    result += f"📍 {space['address']}\n"
                if space.get('contact'):
                    result += f"📞 {space['contact']}\n"
                result += "\n"

            return {
                'success': True,
                'data': [item[0] for item in scored_spaces],
                'count': len(scored_spaces),
                'message': result,
                'keywords': keywords_list
            }
        except Exception as e:
            print(f"복합 키워드 검색 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '복합 키워드 검색 중 오류가 발생했습니다.'
            }

    def get_filter_options(self):
        """청년공간 검색 필터 옵션들 반환"""
        try:
            basic_spaces = get_youth_spaces_data()
            merged_spaces = self.merge_space_data(basic_spaces)

            capacities = set()
            equipment = set()
            types = set()

            for space in merged_spaces:
                if space.get('facility_details'):
                    for facility in space['facility_details']:
                        # 인원수 수집
                        if facility.get('capacity') and facility['capacity'] not in ["명시되지 않음", "없음"]:
                            capacities.add(facility['capacity'])

                        # 구비물품 수집
                        if facility.get('equipment') and facility['equipment'] not in ["명시되지 않음", "기재되지 않음", "없음"]:
                            equipment_list = [eq.strip() for eq in facility['equipment'].split(',')]
                            equipment.update(equipment_list)

                        # 구분(타입) 수집
                        if facility.get('type'):
                            type_list = [t.strip() for t in facility['type'].split('/')]
                            types.update(type_list)

            return {
                'success': True,
                'data': {
                    'capacities': sorted(list(capacities)),
                    'equipment': sorted(list(equipment)),
                    'types': sorted(list(types))
                }
            }
        except Exception as e:
            print(f"필터 옵션 조회 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '필터 옵션을 가져오는 중 오류가 발생했습니다.'
            }

    def search_spaces_for_reservation(self, capacity, equipment_list, space_type):
        """예약을 위한 공간 검색"""
        try:
            basic_spaces = get_youth_spaces_data()
            merged_spaces = self.merge_space_data(basic_spaces)

            results = []

            for space in merged_spaces:
                if space.get('facility_details'):
                    for facility in space['facility_details']:
                        matches = True

                        # 인원수 체크 (필수)
                        if capacity and facility.get('capacity'):
                            if facility['capacity'] not in ["명시되지 않음", "없음"]:
                                # 범위 형태 체크 (예: "10~20명", "20-25명")
                                capacity_match = False
                                facility_capacity = facility['capacity']

                                # 범위 패턴 확인
                                import re
                                range_match = re.search(r'(\d+)[-~](\d+)', facility_capacity)
                                if range_match:
                                    min_cap = int(range_match.group(1))
                                    max_cap = int(range_match.group(2))
                                    selected_num = int(re.search(r'\d+', capacity).group()) if re.search(r'\d+',
                                                                                                         capacity) else 0
                                    if min_cap <= selected_num <= max_cap:
                                        capacity_match = True
                                elif capacity == facility_capacity:
                                    capacity_match = True

                                if not capacity_match:
                                    matches = False

                        # 구비물품 체크 (선택사항)
                        if equipment_list and len(equipment_list) > 0:
                            if facility.get('equipment') and facility['equipment'] not in ["명시되지 않음", "기재되지 않음", "없음"]:
                                facility_equipment = facility['equipment'].lower()
                                has_all_equipment = all(
                                    any(eq.lower() in facility_equipment for eq in [item, item.replace(' ', '')])
                                    for item in equipment_list
                                )
                                if not has_all_equipment:
                                    matches = False
                            else:
                                matches = False

                        # 구분(타입) 체크 (선택사항)
                        if space_type:
                            if facility.get('type'):
                                if space_type.lower() not in facility['type'].lower():
                                    matches = False
                            else:
                                matches = False

                        if matches:
                            # 추가 정보 가져오기
                            space_info = space.copy()
                            booking_link = ""

                            # 예약 링크 찾기
                            for link_key in ['rental_link', 'booking_url', 'rental_form']:
                                if space_info.get(link_key) and space_info[link_key] not in ["없음", ""]:
                                    booking_link = space_info[link_key]
                                    break

                            results.append({
                                'spaceName': space['name'],
                                'spaceRegion': space.get('region', ''),
                                'spaceAddress': space.get('address', ''),
                                'spaceContact': space.get('contact', ''),
                                'facility': {
                                    'name': facility['name'],
                                    'capacity': facility.get('capacity', '명시되지 않음'),
                                    'type': facility.get('type', ''),
                                    'equipment': facility.get('equipment', '명시되지 않음'),
                                    'price': facility.get('price', '없음'),
                                    'notice': facility.get('notice', '없음')
                                },
                                'bookingLink': booking_link,
                                'targetUsers': space.get('target_users', ''),
                                'keywords': space.get('keywords', [])
                            })

            return {
                'success': True,
                'data': results,
                'count': len(results),
                'searchConditions': {
                    'capacity': capacity,
                    'equipment': equipment_list,
                    'type': space_type
                }
            }
        except Exception as e:
            print(f"예약용 공간 검색 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '공간 검색 중 오류가 발생했습니다.'
            }

    def get_all_spaces_formatted(self):
        """전체 청년공간 목록 (포맷된)"""
        try:
            result_message = get_all_youth_spaces()
            return {
                'success': True,
                'message': result_message
            }
        except Exception as e:
            print(f"전체 청년공간 API 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '청년공간 목록을 가져오는 중 오류가 발생했습니다.'
            }

    def crawl_spaces_manually(self):
        """수동 청년공간 크롤링"""
        try:
            print("수동 청년공간 크롤링 요청 받음")
            from services.youth_space_crawler import BusanYouthSpaceCrawler
            import json
            import os
            from datetime import datetime

            crawler = BusanYouthSpaceCrawler()
            spaces = crawler.crawl_all_spaces()

            # 캐시에 저장
            basedir = os.path.abspath(os.path.dirname(__file__))
            project_root = os.path.dirname(basedir)
            instance_path = os.path.join(os.environ.get('RENDER_DISK_PATH', project_root), 'instance')
            if not os.path.exists(instance_path):
                os.makedirs(instance_path)

            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'data': spaces
            }

            cache_file = os.path.join(instance_path, 'youth_spaces_cache.json')
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            return {
                'success': True,
                'data': spaces,
                'count': len(spaces),
                'message': f'크롤링 완료! {len(spaces)}개의 청년공간을 수집했습니다.',
                'crawled_at': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"수동 크롤링 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '크롤링 중 오류가 발생했습니다.'
            }


# 전역 인스턴스 생성
space_handler = SpaceHandler()