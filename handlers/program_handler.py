import os
import json
from datetime import datetime

from services.youth_program_crawler import (
    get_youth_programs_data,
    search_programs_by_region,
    BusanYouthProgramCrawler
)
from handlers.base_handler import BaseHandler


class ProgramHandler(BaseHandler):

    def get_all_programs(self):
        """전체 프로그램 목록"""
        try:
            programs = get_youth_programs_data()
            return {
                'success': True,
                'data': programs,
                'count': len(programs),
                'message': f'{len(programs)}개의 모집중인 프로그램을 찾았습니다.'
            }
        except Exception as e:
            return self.handle_error(e, '프로그램 정보를 가져오는')

    def get_programs_by_region(self, region):
        """지역별 프로그램 검색"""
        try:
            result_message = search_programs_by_region(region)
            programs = get_youth_programs_data()

            region_normalized = region.replace('구', '') if region.endswith('구') else region
            filtered_programs = self._filter_programs_by_region(programs, region_normalized)

            return {
                'success': True,
                'data': filtered_programs,
                'count': len(filtered_programs),
                'message': result_message,
                'region': region
            }
        except Exception as e:
            return self.handle_error(e, f'{region} 지역의 프로그램 정보를 가져오는')

    def _filter_programs_by_region(self, programs, region_normalized):
        """지역별 프로그램 필터링"""
        filtered_programs = []
        for program in programs:
            program_fields = [
                program.get('region', ''),
                program.get('location', ''),
                program.get('title', '')
            ]

            if any(region_normalized in field for field in program_fields):
                filtered_programs.append(program)

        return filtered_programs

    def crawl_programs_manually(self):
        """수동 프로그램 크롤링 - config 폴더에 저장"""
        try:
            crawler = BusanYouthProgramCrawler()
            programs = crawler.crawl_all_programs()

            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'data': programs
            }

            config_path = self.get_config_path()
            cache_file = os.path.join(config_path, 'youth_programs_cache.json')

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            return {
                'success': True,
                'data': programs,
                'count': len(programs),
                'message': f'크롤링 완료! {len(programs)}개의 모집중인 프로그램을 수집했습니다.',
                'crawled_at': datetime.now().isoformat(),
                'saved_to': cache_file
            }
        except Exception as e:
            return self.handle_error(e, '크롤링')

    def search_programs_by_keyword(self, keyword):
        """키워드별 프로그램 검색"""
        try:
            programs = get_youth_programs_data()
            if not programs:
                return {
                    'success': False,
                    'message': '현재 프로그램 정보를 가져올 수 없습니다.'
                }

            keyword_lower = keyword.lower()
            filtered_programs = [
                program for program in programs
                if any(keyword_lower in str(program.get(field, '')).lower()
                       for field in ['title', 'location', 'region'])
            ]

            return {
                'success': True,
                'data': filtered_programs,
                'count': len(filtered_programs),
                'keyword': keyword,
                'message': f'{keyword} 관련 {len(filtered_programs)}개 프로그램을 찾았습니다.'
            }
        except Exception as e:
            return self.handle_error(e, '프로그램 검색')


program_handler = ProgramHandler()