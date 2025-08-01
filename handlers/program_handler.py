import os
import json
from datetime import datetime

from services.youth_program_crawler import (
    get_youth_programs_data,
    search_programs_by_region,
    BusanYouthProgramCrawler
)


class ProgramHandler:
    def get_all_programs(self):
        """전체 프로그램 목록 (기존 로직 완벽 보존)"""
        try:
            programs = get_youth_programs_data()
            return {
                'success': True,
                'data': programs,
                'count': len(programs),
                'message': f'{len(programs)}개의 모집중인 프로그램을 찾았습니다.'
            }
        except Exception as e:
            print(f"프로그램 API 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '프로그램 정보를 가져오는 중 오류가 발생했습니다.'
            }

    def get_programs_by_region(self, region):
        """지역별 프로그램 검색 (기존 로직 완벽 보존)"""
        try:
            result_message = search_programs_by_region(region)
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

            return {
                'success': True,
                'data': filtered_programs,
                'count': len(filtered_programs),
                'message': result_message,
                'region': region
            }
        except Exception as e:
            print(f"지역별 프로그램 API 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'{region} 지역의 프로그램 정보를 가져오는 중 오류가 발생했습니다.'
            }

    def crawl_programs_manually(self):
        """수동 프로그램 크롤링 (기존 로직 완벽 보존)"""
        try:
            print("수동 크롤링 요청 받음")

            crawler = BusanYouthProgramCrawler()
            programs = crawler.crawl_all_programs()

            # 캐시에 저장
            basedir = os.path.abspath(os.path.dirname(__file__))
            project_root = os.path.dirname(basedir)
            instance_path = os.path.join(os.environ.get('RENDER_DISK_PATH', project_root), 'instance')
            if not os.path.exists(instance_path):
                os.makedirs(instance_path)

            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'data': programs
            }

            cache_file = os.path.join(instance_path, 'youth_programs_cache.json')
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            return {
                'success': True,
                'data': programs,
                'count': len(programs),
                'message': f'크롤링 완료! {len(programs)}개의 모집중인 프로그램을 수집했습니다.',
                'crawled_at': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"수동 크롤링 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '크롤링 중 오류가 발생했습니다.'
            }

    def search_programs_by_keyword(self, keyword):
        """키워드별 프로그램 검색"""
        try:
            programs = get_youth_programs_data()
            if not programs:
                return {
                    'success': False,
                    'message': '현재 프로그램 정보를 가져올 수 없습니다.'
                }

            filtered_programs = []
            keyword_lower = keyword.lower()

            for program in programs:
                if (keyword_lower in program.get('title', '').lower() or
                        keyword_lower in program.get('location', '').lower() or
                        keyword_lower in program.get('region', '').lower()):
                    filtered_programs.append(program)

            return {
                'success': True,
                'data': filtered_programs,
                'count': len(filtered_programs),
                'keyword': keyword,
                'message': f'{keyword} 관련 {len(filtered_programs)}개 프로그램을 찾았습니다.'
            }
        except Exception as e:
            print(f"키워드 검색 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '프로그램 검색 중 오류가 발생했습니다.'
            }


# 전역 인스턴스 생성
program_handler = ProgramHandler()