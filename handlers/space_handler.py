import json
import os
from datetime import datetime
from services.youth_space_crawler import get_youth_spaces_data
from handlers.base_handler import BaseHandler


class SpaceHandler(BaseHandler):
    def __init__(self):
        pass

    def load_overrides_data(self):
        """youth_spaces_overrides.json 데이터 로드 (config/ 우선, instance/ 폴백)"""
        for base_path in [self.get_config_path(), self.get_instance_path()]:
            overrides_file = os.path.join(base_path, 'youth_spaces_overrides.json')
            try:
                if os.path.exists(overrides_file):
                    with open(overrides_file, 'r', encoding='utf-8') as f:
                        return json.load(f).get('data', [])
            except Exception:
                continue
        return []

    def merge_spaces_data(self, cache_spaces, override_spaces):
        """캐시 데이터와 Override 데이터 병합"""
        merged_spaces = []

        override_dict = {space.get('name', ''): space for space in override_spaces}

        for cache_space in cache_spaces:
            space_name = cache_space.get('name', '')
            if space_name in override_dict:
                merged_spaces.append(override_dict[space_name])
            else:
                merged_spaces.append(cache_space)

        cache_names = {space.get('name', '') for space in cache_spaces}
        for override_space in override_spaces:
            if override_space.get('name', '') not in cache_names:
                merged_spaces.append(override_space)

        return merged_spaces

    def get_merged_spaces_data(self):
        """캐시 데이터와 Override 데이터를 병합하여 반환"""
        try:
            cache_spaces = get_youth_spaces_data()
            override_spaces = self.load_overrides_data()
            merged_spaces = self.merge_spaces_data(cache_spaces, override_spaces)

            return merged_spaces
        except Exception:
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
            return self.handle_error(e, '청년공간 정보를 가져오는')

    def _format_space_links(self, space):
        """공간의 링크 정보 포맷팅"""
        links = []
        link_mapping = [
            ('homepage', '홈페이지'),
            ('rental_link', '대관신청'),
            ('program_link', '프로그램'),
            ('sns', 'SNS')
        ]

        for field, label in link_mapping:
            if space.get(field):
                links.append(f"[{label}]({space[field]})")

        return links

    def get_space_detail(self, space_name):
        """특정 공간의 상세 정보 (Override 적용)"""
        try:
            spaces = self.get_merged_spaces_data()

            target_space = next(
                (space for space in spaces
                 if space_name.lower() in space.get('name', '').lower()),
                None
            )

            if not target_space:
                return {
                    'success': False,
                    'message': f'"{space_name}"와 관련된 공간을 찾을 수 없습니다.'
                }

            result = f"**🏢 {target_space['name']}** [{target_space.get('region', '')}]\n\n"

            info_fields = [
                ('address', '📍', '주소'),
                ('contact', '📞', '연락처'),
                ('hours', '🕒', '이용시간'),
                ('description', '📝', '설명')
            ]

            for field, emoji, label in info_fields:
                if target_space.get(field):
                    result += f"{emoji} **{label}**: {target_space[field]}\n"

            links = self._format_space_links(target_space)
            if links:
                result += f"\n🔗 **관련 링크**: {' | '.join(links)}\n"

            return {
                'success': True,
                'data': target_space,
                'message': result
            }
        except Exception as e:
            return self.handle_error(e, '공간 상세 정보를 가져오는')

    def _format_space_basic_info(self, space):
        """공간의 기본 정보 포맷팅"""
        result = f"**{space['name']}[{space.get('region', '')}]**\n"

        basic_fields = [
            ('address', '📍'),
            ('contact', '📞')
        ]

        for field, emoji in basic_fields:
            if space.get(field):
                result += f"{emoji} {space[field]}\n"

        return result + "\n"

    def get_spaces_by_region(self, region):
        """지역별 청년공간 검색 (Override 적용)"""
        try:
            spaces = self.get_merged_spaces_data()

            filtered_spaces = [
                space for space in spaces
                if space.get('region', '').strip() == region
            ]

            if not filtered_spaces:
                return {
                    'success': False,
                    'message': f'**{region}**에서 청년공간을 찾을 수 없습니다.\n\n다른 지역을 검색해보세요!'
                }

            result = f"{region} 청년공간({len(filtered_spaces)}개)\n\n"

            for space in filtered_spaces[:5]:
                result += self._format_space_basic_info(space)

            return {
                'success': True,
                'data': filtered_spaces,
                'count': len(filtered_spaces),
                'message': result,
                'region': region
            }
        except Exception as e:
            return self.handle_error(e, f'{region} 지역의 청년공간 정보를 가져오는')

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
            keyword_lower = keyword.lower()

            filtered_spaces = [
                space for space in spaces
                if any(keyword_lower in str(space.get(field, '')).lower()
                       for field in ['name', 'description', 'region'])
            ]

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
                    desc = space['description']
                    if len(desc) > 100:
                        desc = desc[:100] + "..."
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
            return self.handle_error(e, '청년공간 검색')

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
                regions.setdefault(region, []).append(space['name'])

            for region, names in sorted(regions.items()):
                result += f"📍 {region} ({len(names)}개)\n"
                for name in names:
                    result += f"\u00A0\u00A0{name}\n"
                result += "\n"

            result += "💡 지역명이나 공간명으로 자세한 정보를 검색해보세요!"

            return {
                'success': True,
                'message': result
            }
        except Exception as e:
            return self.handle_error(e, '청년공간 목록을 가져오는')

    def crawl_spaces_manually(self):
        """수동 청년공간 크롤링"""
        try:
            from services.youth_space_crawler import BusanYouthSpaceCrawler

            crawler = BusanYouthSpaceCrawler()
            spaces = crawler.crawl_all_spaces()

            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'data': spaces
            }

            cache_file = os.path.join(self.get_instance_path(), 'youth_spaces_cache.json')
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
            return self.handle_error(e, '크롤링')


space_handler = SpaceHandler()