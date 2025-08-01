from services.youth_space_crawler import (
    get_youth_spaces_data,
    search_spaces_by_region,
    search_spaces_by_keyword,
    get_all_youth_spaces
)


class SpaceHandler:
    def get_all_spaces(self):
        """전체 청년공간 목록"""
        try:
            spaces = get_youth_spaces_data()
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

    def get_spaces_by_region(self, region):
        """지역별 청년공간 검색"""
        try:
            result_message = search_spaces_by_region(region)
            spaces = get_youth_spaces_data()

            # 해당 지역 공간 필터링
            filtered_spaces = [s for s in spaces if region.lower() in s.get('region', '').lower()]

            return {
                'success': True,
                'data': filtered_spaces,
                'count': len(filtered_spaces),
                'message': result_message,
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
        """키워드별 청년공간 검색"""
        try:
            if not keyword:
                return {
                    'success': False,
                    'error': '검색 키워드가 필요합니다.',
                    'message': '검색 키워드를 입력해주세요.'
                }

            result_message = search_spaces_by_keyword(keyword)
            spaces = get_youth_spaces_data()

            # 키워드로 필터링
            filtered_spaces = []
            keyword_lower = keyword.lower()

            for space in spaces:
                if (keyword_lower in space.get('name', '').lower() or
                        keyword_lower in space.get('description', '').lower() or
                        keyword_lower in space.get('region', '').lower()):
                    filtered_spaces.append(space)

            return {
                'success': True,
                'data': filtered_spaces,
                'count': len(filtered_spaces),
                'message': result_message,
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