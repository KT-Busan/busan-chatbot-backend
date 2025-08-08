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
            print(f"페이지 요청: {url}")
            response = self.session.get(url, timeout=15)
            response.encoding = encoding

            if response.status_code == 200:
                return BeautifulSoup(response.content, 'html.parser')
            else:
                print(f"HTTP 오류: {response.status_code}")
                return None

        except Exception as e:
            print(f"페이지 로드 오류: {e}")
            return None

    def extract_space_info_from_li(self, li_element, order):
        """li.toggle_type 요소에서 공간 정보 추출"""
        try:
            space_info = {
                'region': '',
                'name': '',
                'contact': '',
                'description': '',
                'address': '',
                'hours': '',
                'homepage': '',
                'sns': '',
                'rental_link': '',
                'program_link': ''
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
                            elif '연락처' in label:
                                if not space_info['contact']:
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

            if space_info['name'] and space_info['region']:
                return space_info
            else:
                return None

        except Exception as e:
            print(f"li 요소 파싱 오류: {e}")
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
            except Exception as e:
                continue

        return spaces

    def has_space_content(self, soup):
        """페이지에 공간 콘텐츠가 있는지 확인"""
        if not soup:
            return False
        toggle_items = soup.select('.toggle_type')
        return len(toggle_items) > 0

    def crawl_all_spaces(self):
        """모든 청년공간 크롤링"""
        print("부산 청년공간 크롤링 시작")
        all_spaces = []

        for page in range(1, 4):
            print(f"페이지 {page}/3 크롤링 중...")

            if page == 1:
                url = "https://young.busan.go.kr/space/list.nm"
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

            if page == 1:
                soup = self.get_page_content(url)

            if not soup:
                continue

            page_spaces = self.extract_spaces_from_page(soup, page)
            all_spaces.extend(page_spaces)
            time.sleep(1)  # 페이지 간 지연

        print(f"크롤링 완료: {len(all_spaces)}개 공간 수집")
        self.spaces_data = all_spaces
        return all_spaces


def load_overrides_data():
    """youth_spaces_overrides.json 데이터 로드"""
    try:
        basedir = os.path.abspath(os.path.dirname(__file__))
        project_root = os.path.dirname(basedir)
        instance_path = os.path.join(os.environ.get('RENDER_DISK_PATH', project_root), 'instance')

        overrides_file = os.path.join(instance_path, 'youth_spaces_overrides.json')

        if os.path.exists(overrides_file):
            with open(overrides_file, 'r', encoding='utf-8') as f:
                overrides_data = json.load(f)
            print(f"✅ Override 데이터 로드: {len(overrides_data.get('data', []))}개")
            return overrides_data.get('data', [])
        else:
            print("ℹ️ youth_spaces_overrides.json 파일이 없습니다.")
            return []
    except Exception as e:
        print(f"❌ Override 데이터 로드 오류: {e}")
        return []


def merge_spaces_data(cache_spaces, override_spaces):
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


def crawl_new_data():
    """새로운 데이터 크롤링 및 캐시 저장"""
    try:
        print("🔄 새로운 청년공간 데이터 크롤링 중...")
        crawler = BusanYouthSpaceCrawler()
        spaces = crawler.crawl_all_spaces()

        # 캐시 저장
        basedir = os.path.abspath(os.path.dirname(__file__))
        project_root = os.path.dirname(basedir)
        instance_path = os.path.join(os.environ.get('RENDER_DISK_PATH', project_root), 'instance')

        cache_data = {
            'cached_at': datetime.now().isoformat(),
            'data': spaces
        }

        cache_file = os.path.join(instance_path, 'youth_spaces_cache.json')
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print("💾 청년공간 캐시 저장 완료")

        return spaces
    except Exception as e:
        print(f"❌ 크롤링 오류: {e}")
        return []


def get_cache_data_only():
    """캐시 데이터만 가져오기 (Override 적용 안함)"""
    basedir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.dirname(basedir)
    instance_path = os.path.join(os.environ.get('RENDER_DISK_PATH', project_root), 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)

    cache_file = os.path.join(instance_path, 'youth_spaces_cache.json')
    cache_duration = timedelta(hours=24)

    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            cache_time = datetime.fromisoformat(cached_data['cached_at'])
            if datetime.now() - cache_time < cache_duration:
                print("📋 캐시된 청년공간 데이터 사용")
                return cached_data['data']
            else:
                print("⏰ 캐시가 만료되어 새로운 데이터 크롤링")
                return crawl_new_data()
        except Exception as e:
            print(f"❌ 캐시 읽기 오류: {e}")
            return crawl_new_data()
    else:
        print("🔄 캐시 파일이 없어 새로운 데이터 크롤링")
        return crawl_new_data()


def get_youth_spaces_data():
    """청년공간 데이터 가져오기 (Override 적용)"""
    # 캐시 데이터 로드
    cache_spaces = get_cache_data_only()

    # Override 데이터 로드
    override_spaces = load_overrides_data()

    # 데이터 병합
    merged_spaces = merge_spaces_data(cache_spaces, override_spaces)

    print(f"📊 최종 데이터: 캐시 {len(cache_spaces)}개 + Override {len(override_spaces)}개 = 병합 {len(merged_spaces)}개")

    return merged_spaces


def search_spaces_by_region(region):
    """지역별 청년공간 검색 (Override 적용)"""
    spaces = get_youth_spaces_data()
    if not spaces:
        return "현재 청년공간 정보를 가져올 수 없습니다."

    filtered_spaces = []
    for space in spaces:
        space_region = space.get('region', '').strip()
        if space_region == region:
            filtered_spaces.append(space)

    if not filtered_spaces:
        return f"**{region}**에서 청년공간을 찾을 수 없습니다.\n\n다른 지역을 검색해보세요!"

    result = f"**{region} 청년공간({len(filtered_spaces)}개)**\n\n"

    for space in filtered_spaces[:5]:
        result += format_space_info(space) + "\n"

    return result


def search_spaces_by_keyword(keyword):
    """키워드별 청년공간 검색 (Override 적용)"""
    spaces = get_youth_spaces_data()
    if not spaces:
        return "현재 청년공간 정보를 가져올 수 없습니다."

    filtered_spaces = []
    keyword_lower = keyword.lower()

    for space in spaces:
        if (keyword_lower in space.get('name', '').lower() or
                keyword_lower in space.get('description', '').lower() or
                keyword_lower in space.get('region', '').lower()):
            filtered_spaces.append(space)

    if not filtered_spaces:
        return f"**{keyword}** 관련 청년공간을 찾을 수 없습니다.\n\n다른 키워드로 검색해보세요!"

    result = f"🔍 **{keyword}** 검색 결과 ({len(filtered_spaces)}개)\n\n"

    for space in filtered_spaces[:5]:
        result += format_space_info(space) + "\n"

    return result


def format_space_info(space):
    """공간 정보 포맷팅"""
    result = f"**{space['name']}[{space.get('region', '')}]**\n"

    if space.get('address'):
        result += f"📍 {space['address']}\n"
    if space.get('contact'):
        result += f"📞 {space['contact']}\n"
    if space.get('hours'):
        result += f"🕒 {space['hours']}\n"
    if space.get('description'):
        desc = space['description'][:100] + "..." if len(space['description']) > 100 else space['description']
        result += f"📝 {desc}\n"

    links = []
    if space.get('homepage'):
        links.append(f"[홈페이지]({space['homepage']})")
    if space.get('rental_link'):
        links.append(f"[대관신청]({space['rental_link']})")
    if space.get('program_link'):
        links.append(f"[프로그램]({space['program_link']})")

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
        if region not in regions:
            regions[region] = []
        regions[region].append(space['name'])

    for region, names in sorted(regions.items()):
        result += f"**📍 {region}** ({len(names)}개)\n"
        for name in names:
            result += f"  • {name}\n"
        result += "\n"

    result += "💡 지역명이나 공간명으로 자세한 정보를 검색해보세요!"
    return result