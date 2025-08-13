import requests
import re
import time
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
from datetime import datetime, timedelta


class BusanYouthSpaceCrawler:
    def __init__(self):
        self.base_url = "https://young.busan.go.kr"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.spaces_data = []

    def get_page_content(self, url, encoding='utf-8'):
        """페이지 내용 가져오기"""
        try:
            response = self.session.get(url, timeout=15)
            response.encoding = encoding

            if response.status_code == 200:
                return BeautifulSoup(response.content, 'html.parser')
            return None
        except Exception:
            return None

    def extract_space_info_from_li(self, li_element, order):
        """li.toggle_type 요소에서 공간 정보 추출"""
        try:
            space_info = {
                'region': '', 'name': '', 'contact': '', 'description': '',
                'address': '', 'hours': '', 'homepage': '', 'sns': '',
                'rental_link': '', 'program_link': ''
            }

            plc_box = li_element.select_one('a.toggle .plc_box')
            if plc_box:
                plc_gu = plc_box.select_one('.plc_gu')
                if plc_gu:
                    space_info['region'] = plc_gu.get_text(strip=True)

                plc_tit = plc_box.select_one('.plc_tit')
                if plc_tit:
                    spans = plc_tit.find_all('span')
                    if len(spans) >= 2:
                        space_info['name'] = spans[1].get_text(strip=True)

                plc_part = plc_box.select_one('.plc_part')
                if plc_part:
                    space_info['contact'] = plc_part.get_text(strip=True)

            toggle_inner = li_element.select_one('.toggle_inner')
            if toggle_inner:
                spif_con = toggle_inner.select_one('.spif_con')
                if spif_con:
                    space_info['description'] = spif_con.get_text(strip=True)

                arrow_list = toggle_inner.select_one('.arrow_list ul')
                if arrow_list:
                    li_items = arrow_list.find_all('li')
                    for li_item in li_items:
                        spans = li_item.find_all('span')
                        if len(spans) >= 2:
                            label = spans[0].get_text(strip=True)
                            value = spans[1].get_text(strip=True)

                            if '주소' in label:
                                space_info['address'] = value
                            elif '이용시간' in label or '운영시간' in label:
                                space_info['hours'] = value
                            elif '연락처' in label and not space_info['contact']:
                                space_info['contact'] = value

                splink_list = toggle_inner.select('.splink_list a')
                for link in splink_list:
                    link_text = link.select_one('.splink_txt')
                    if link_text:
                        text = link_text.get_text(strip=True)
                        href = link.get('href', '')

                        if '홈페이지' in text:
                            space_info['homepage'] = href
                        elif 'SNS' in text:
                            space_info['sns'] = href
                        elif '대관' in text:
                            space_info['rental_link'] = href
                        elif '프로그램' in text:
                            space_info['program_link'] = href

            return space_info if space_info['name'] and space_info['region'] else None

        except Exception:
            return None

    def extract_spaces_from_page(self, soup, page_num):
        """페이지에서 청년공간 목록 추출"""
        spaces = []
        space_list = soup.select('.policy_list.space_list ul li.toggle_type')

        for i, li_element in enumerate(space_list, 1):
            try:
                space_info = self.extract_space_info_from_li(li_element, i)
                if space_info:
                    spaces.append(space_info)
            except Exception:
                continue

        return spaces

    def has_space_content(self, soup):
        """페이지에 공간 콘텐츠가 있는지 확인"""
        if not soup:
            return False
        return len(soup.select('.toggle_type')) > 0

    def crawl_all_spaces(self):
        """모든 청년공간 크롤링"""
        all_spaces = []

        for page in range(1, 4):
            if page == 1:
                url = "https://young.busan.go.kr/space/list.nm"
                soup = self.get_page_content(url)
            else:
                possible_urls = [
                    f"https://young.busan.go.kr/space/list.nm?pageIndex={page}",
                    f"https://young.busan.go.kr/space/list.nm?page={page}",
                ]

                soup = None
                for url in possible_urls:
                    soup = self.get_page_content(url)
                    if soup and self.has_space_content(soup):
                        break
                    time.sleep(0.5)

                if not soup:
                    continue

            if not soup:
                continue

            page_spaces = self.extract_spaces_from_page(soup, page)
            all_spaces.extend(page_spaces)
            time.sleep(1)

        self.spaces_data = all_spaces
        return all_spaces


def get_instance_path():
    """인스턴스 경로 반환 - 런타임 캐시용"""
    basedir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.dirname(basedir)
    instance_path = os.path.join(os.environ.get('RENDER_DISK_PATH', project_root), 'instance')
    os.makedirs(instance_path, exist_ok=True)
    return instance_path


def get_config_path():
    """config 경로 반환 - 정적 파일용"""
    basedir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.dirname(basedir)
    config_path = os.path.join(project_root, 'config')
    os.makedirs(config_path, exist_ok=True)
    return config_path


def get_cache_file_path():
    """캐시 파일 경로 반환 - config 폴더 우선, 없으면 instance"""
    config_file = os.path.join(get_config_path(), 'youth_spaces_cache.json')
    instance_file = os.path.join(get_instance_path(), 'youth_spaces_cache.json')

    if os.path.exists(config_file):
        print(f"🔧 config에서 캐시 파일 사용: {config_file}")
        return config_file

    print(f"🔧 instance에서 캐시 파일 사용: {instance_file}")
    return instance_file


def get_overrides_file_path():
    """Override 파일 경로 반환"""
    overrides_file = os.path.join(get_instance_path(), 'youth_spaces_overrides.json')
    print(f"🔧 overrides_file_path: {overrides_file}")
    return overrides_file


def save_to_config_file(spaces_data):
    """config 폴더에 정적 파일로 저장 (Git에 포함됨)"""
    try:
        config_file = os.path.join(get_config_path(), 'youth_spaces_cache.json')
        cache_data = {
            'cached_at': datetime.now().isoformat(),
            'data': spaces_data
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

        print(f"✅ config 폴더에 센터 데이터 저장: {config_file}")
        return True
    except Exception as e:
        print(f"❌ config 저장 실패: {str(e)}")
        return False


def load_overrides_data():
    """youth_spaces_overrides.json 데이터 로드"""
    try:
        overrides_file = get_overrides_file_path()

        if os.path.exists(overrides_file):
            with open(overrides_file, 'r', encoding='utf-8') as f:
                overrides_data = json.load(f)
            return overrides_data.get('data', [])
        return []
    except Exception:
        return []


def merge_spaces_data(cache_spaces, override_spaces):
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


def crawl_new_data():
    """새로운 데이터 크롤링 및 캐시 저장"""
    try:
        crawler = BusanYouthSpaceCrawler()
        spaces = crawler.crawl_all_spaces()

        save_to_config_file(spaces)

        cache_data = {
            'cached_at': datetime.now().isoformat(),
            'data': spaces
        }

        cache_file = get_cache_file_path()
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

        return spaces
    except Exception:
        return []


def get_cache_data_only():
    """캐시 데이터만 가져오기 - config 우선, 없으면 크롤링"""
    cache_file = get_cache_file_path()
    cache_duration = timedelta(hours=24)

    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            if 'config' in cache_file:
                print(f"✅ config 파일에서 센터 데이터 로드: {len(cached_data.get('data', []))}개")
                return cached_data['data']

            cache_time = datetime.fromisoformat(cached_data['cached_at'])
            if datetime.now() - cache_time < cache_duration:
                return cached_data['data']
            else:
                return crawl_new_data()
        except Exception:
            return crawl_new_data()
    else:
        return crawl_new_data()


def get_youth_spaces_data():
    """청년공간 데이터 가져오기 (Override 적용)"""
    cache_spaces = get_cache_data_only()
    override_spaces = load_overrides_data()
    merged_spaces = merge_spaces_data(cache_spaces, override_spaces)

    return merged_spaces


def search_spaces_by_region(region):
    """지역별 청년공간 검색 (Override 적용) - 구분선 추가"""
    spaces = get_youth_spaces_data()
    if not spaces:
        return "현재 청년공간 정보를 가져올 수 없습니다."

    filtered_spaces = [
        space for space in spaces
        if space.get('region', '').strip() == region
    ]

    if not filtered_spaces:
        return f"**{region}**에서 청년공간을 찾을 수 없습니다.\n\n다른 지역을 검색해보세요!"

    result = f"**{region} 청년공간({len(filtered_spaces)}개)**\n\n"

    for i, space in enumerate(filtered_spaces[:5]):
        result += format_space_info(space)

        if i < len(filtered_spaces[:5]) - 1:
            result += "---\n"

    return result


def search_spaces_by_keyword(keyword):
    """키워드별 청년공간 검색 (Override 적용) - 구분선 추가"""
    spaces = get_youth_spaces_data()
    if not spaces:
        return "현재 청년공간 정보를 가져올 수 없습니다."

    keyword_lower = keyword.lower()
    filtered_spaces = [
        space for space in spaces
        if any(keyword_lower in str(space.get(field, '')).lower()
               for field in ['name', 'description', 'region'])
    ]

    if not filtered_spaces:
        return f"**{keyword}** 관련 청년공간을 찾을 수 없습니다.\n\n다른 키워드로 검색해보세요!"

    result = f"🔍 **{keyword}** 검색 결과 ({len(filtered_spaces)}개)\n\n"

    for i, space in enumerate(filtered_spaces[:5]):
        result += format_space_info(space)

        if i < len(filtered_spaces[:5]) - 1:
            result += "---\n"

    return result


def format_space_info(space):
    """공간 정보 포맷팅"""
    result = f"**{space['name']}[{space.get('region', '')}]**\n"

    info_fields = [
        ('address', '📍'),
        ('contact', '📞'),
        ('hours', '🕒')
    ]

    for field, emoji in info_fields:
        if space.get(field):
            result += f"{emoji} {space[field]}\n"

    if space.get('description'):
        desc = space['description']
        if len(desc) > 100:
            desc = desc[:100] + "..."
        result += f"📝 {desc}\n"

    links = []
    link_mapping = [
        ('homepage', '홈페이지'),
        ('rental_link', '대관신청'),
        ('program_link', '프로그램')
    ]

    for field, label in link_mapping:
        if space.get(field):
            links.append(f"[{label}]({space[field]})")

    if links:
        result += f"🔗 {' | '.join(links)}\n"

    return result


def get_all_youth_spaces():
    """전체 청년공간 목록 (Override 적용)"""
    spaces = get_youth_spaces_data()
    if not spaces:
        return "현재 청년공간 정보를 가져올 수 없습니다."

    result = f"**부산 청년공간 전체 목록** ({len(spaces)}개)\n\n"

    regions = {}
    for space in spaces:
        region = space.get('region', '기타')
        regions.setdefault(region, []).append(space['name'])

    for region, names in sorted(regions.items()):
        result += f"**📍 {region}** ({len(names)}개)\n"
        for name in names:
            result += f"  • {name}\n"
        result += "\n"

    result += "💡 지역명이나 공간명으로 자세한 정보를 검색해보세요!"
    return result
