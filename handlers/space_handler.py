import json
import os
from services.youth_space_crawler import (
    get_youth_spaces_data,
    search_spaces_by_region,
    search_spaces_by_keyword,
    get_all_youth_spaces
)


class SpaceHandler:
    def __init__(self):
        pass

    def load_overrides_data(self):
        """youth_spaces_overrides.json 데이터 로드"""
        try:
            basedir = os.path.abspath(os.path.dirname(__file__))
            project_root = os.path.dirname(basedir)
            instance_path = os.path.join(os.environ.get('RENDER_DISK_PATH', project_root), 'instance')

            overrides_file = os.path.join(instance_path, 'youth_spaces_overrides.json')

            if os.path.exists(overrides_file):
                with open(overrides_file, 'r', encoding='utf-8') as f:
                    overrides_data = json.load(f)
                return overrides_data.get('data', [])
            else:
                print("youth_spaces_overrides.json 파일이 없습니다.")
                return []
        except Exception as e:
            print(f"Override 데이터 로드 오류: {e}")
            return []

    def merge_spaces_data(self, cache_spaces, override_spaces):
        """캐시 데이터와 Override 데이터 병합"""
        merged_spaces = []
        override_dict = {}

        # Override 데이터를 딕셔너리로 변환 (name을 키로 사용)
        for space in override_spaces:
            override_dict[space.get('name', '')] = space

        # 캐시 데이터를 순회하면서 Override가 있으면 교체, 없으면 원본 사용
        for cache_space in cache_spaces:
            space_name = cache_space.get('name', '')
            if space_name in override_dict:
                # Override 데이터 사용
                merged_spaces.append(override_dict[space_name])
                print(f"✅ Override 적용: {space_name}")
            else:
                # 원본 캐시 데이터 사용
                merged_spaces.append(cache_space)

        # Override에만 있고 캐시에 없는 새로운 공간들 추가
        cache_names = {space.get('name', '') for space in cache_spaces}
        for override_space in override_spaces:
            if override_space.get('name', '') not in cache_names:
                merged_spaces.append(override_space)
                print(f"✅ 새로운 공간 추가: {override_space.get('name', '')}")

        return merged_spaces

    def get_merged_spaces_data(self):
        """캐시 데이터와 Override 데이터를 병합하여 반환"""
        try:
            # 캐시 데이터 로드
            cache_spaces = get_youth_spaces_data()

            # Override 데이터 로드
            override_spaces = self.load_overrides_data()

            # 데이터 병합
            merged_spaces = self.merge_spaces_data(cache_spaces, override_spaces)

            print(f"📊 데이터 병합 완료: 캐시 {len(cache_spaces)}개 + Override {len(override_spaces)}개 = 최종 {len(merged_spaces)}개")

            return merged_spaces
        except Exception as e:
            print(f"데이터 병합 오류: {e}")
            # 오류 시 캐시 데이터만 반환
            return get_youth_spaces_data()

    def get_all_spaces(self):
        """전체 청년공간 목록 (Override 적용)"""
        try:
            spaces = self.get_merged_spaces_data()
            return {
                'success': True,
                'data': spaces,
                'count': len(spaces),
                'message': f'{len(spaces)}개의 청년공간을 찾았습니다.'
            }
        except Exception as e:
            print(f"청년공간 API 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '청년공간 정보를 가져오는 중 오류가 발생했습니다.'
            }

    def get_space_detail(self, space_name):
        """특정 공간의 상세 정보 (Override 적용)"""
        try:
            spaces = self.get_merged_spaces_data()

            target_space = None
            for space in spaces:
                if space_name.lower() in space.get('name', '').lower():
                    target_space = space
                    break

            if not target_space:
                return {
                    'success': False,
                    'message': f'"{space_name}"와 관련된 공간을 찾을 수 없습니다.'
                }

            result = f"**🏢 {target_space['name']}** [{target_space.get('region', '')}]\n\n"

            if target_space.get('address'):
                result += f"📍 **주소**: {target_space['address']}\n"
            if target_space.get('contact'):
                result += f"📞 **연락처**: {target_space['contact']}\n"
            if target_space.get('hours'):
                result += f"🕒 **이용시간**: {target_space['hours']}\n"
            if target_space.get('description'):
                result += f"📝 **설명**: {target_space['description']}\n"

            links = []
            if target_space.get('homepage'):
                links.append(f"[홈페이지]({target_space['homepage']})")
            if target_space.get('rental_link'):
                links.append(f"[대관신청]({target_space['rental_link']})")
            if target_space.get('program_link'):
                links.append(f"[프로그램]({target_space['program_link']})")
            if target_space.get('sns'):
                links.append(f"[SNS]({target_space['sns']})")

            if links:
                result += f"\n🔗 **관련 링크**: {' | '.join(links)}\n"

            return {
                'success': True,
                'data': target_space,
                'message': result
            }
        except Exception as e:
            print(f"공간 상세 정보 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '공간 상세 정보를 가져오는 중 오류가 발생했습니다.'
            }

    def get_spaces_by_region(self, region):
        """지역별 청년공간 검색 (Override 적용)"""
        try:
            spaces = self.get_merged_spaces_data()

            filtered_spaces = []
            for space in spaces:
                space_region = space.get('region', '').strip()
                if space_region == region:
                    filtered_spaces.append(space)

            if not filtered_spaces:
                return {
                    'success': False,
                    'message': f'**{region}**에서 청년공간을 찾을 수 없습니다.\n\n다른 지역을 검색해보세요!'
                }

            result = f"**{region} 청년공간({len(filtered_spaces)}개)**\n\n"

            for space in filtered_spaces[:5]:
                result += f"**{space['name']}[{space.get('region', '')}]**\n"
                if space.get('address'):
                    result += f"📍 {space['address']}\n"
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
        """키워드별 청년공간 검색 (Override 적용)"""
        try:
            if not keyword:
                return {
                    'success': False,
                    'error': '검색 키워드가 필요합니다.',
                    'message': '검색 키워드를 입력해주세요.'
                }

            spaces = self.get_merged_spaces_data()

            filtered_spaces = []
            keyword_lower = keyword.lower()

            for space in spaces:
                searchable_text = [
                    space.get('name', ''),
                    space.get('description', ''),
                    space.get('region', '')
                ]

                if any(keyword_lower in text.lower() for text in searchable_text):
                    filtered_spaces.append(space)

            if not filtered_spaces:
                return {
                    'success': False,
                    'message': f"**{keyword}** 관련 청년공간을 찾을 수 없습니다.\n\n다른 키워드로 검색해보세요!"
                }

            result = f"🔍 **{keyword}** 검색 결과 ({len(filtered_spaces)}개)\n\n"

            for space in filtered_spaces[:5]:
                result += f"**{space['name']}** [{space.get('region', '')}]\n"
                if space.get('address'):
                    result += f"📍 {space['address']}\n"
                if space.get('description'):
                    desc = space['description'][:100] + "..." if len(space['description']) > 100 else space[
                        'description']
                    result += f"📝 {desc}\n"
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

    def get_all_spaces_formatted(self):
        """전체 청년공간 목록 (포맷된, Override 적용)"""
        try:
            spaces = self.get_merged_spaces_data()

            if not spaces:
                return {
                    'success': False,
                    'message': '현재 청년공간 정보를 가져올 수 없습니다.'
                }

            result = f"**부산 청년공간 전체 목록** ({len(spaces)}개)\n\n"

            regions = {}
            for space in spaces:
                region = space.get('region', '기타')
                if region not in regions:
                    regions[region] = []
                regions[region].append(space['name'])

            for region, names in sorted(regions.items()):
                result += f"**📍 {region}** ({len(names)}개)\n"
                for name in names:
                    result += f"  • {name}\n"
                result += "\n"

            result += "💡 지역명이나 공간명으로 자세한 정보를 검색해보세요!"

            return {
                'success': True,
                'message': result
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


space_handler = SpaceHandler()