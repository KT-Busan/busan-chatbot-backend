import requests
import re
import time
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
from datetime import datetime


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

            # 1. 기본 정보 추출
            plc_box = li_element.select_one('a.toggle .plc_box')
            if plc_box:
                # 지역 정보
                plc_gu = plc_box.select_one('.plc_gu')
                if plc_gu:
                    space_info['region'] = plc_gu.get_text(strip=True)

                # 공간명 추출
                plc_tit = plc_box.select_one('.plc_tit')
                if plc_tit:
                    spans = plc_tit.find_all('span')
                    if len(spans) >= 2:
                        space_info['name'] = spans[1].get_text(strip=True)

                # 연락처
                plc_part = plc_box.select_one('.plc_part')
                if plc_part:
                    space_info['contact'] = plc_part.get_text(strip=True)

            # 2. 상세 정보 추출
            toggle_inner = li_element.select_one('.toggle_inner')
            if toggle_inner:
                # 공간 설명
                spif_con = toggle_inner.select_one('.spif_con')
                if spif_con:
                    space_info['description'] = spif_con.get_text(strip=True)

                # 주소, 이용시간, 연락처 추출
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

                # 링크 정보 추출
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

            # 최소 조건 확인
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

        # 1, 2, 3 페이지 크롤링
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


def get_youth_spaces_data():
    """청년공간 데이터 가져오기"""
    import os
    from datetime import datetime, timedelta

    # 프로젝트 루트의 instance 폴더 경로 설정
    basedir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.dirname(basedir)  # services의 상위 폴더 (프로젝트 루트)
    instance_path = os.path.join(os.environ.get('RENDER_DISK_PATH', project_root), 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)

    cache_file = os.path.join(instance_path, 'youth_spaces_cache.json')
    cache_duration = timedelta(hours=24)  # 24시간 캐시

    # 캐시 파일 확인
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            cache_time = datetime.fromisoformat(cached_data['cached_at'])
            if datetime.now() - cache_time < cache_duration:
                print("캐시된 청년공간 데이터 사용")
                return cached_data['data']
        except Exception as e:
            print(f"캐시 읽기 오류: {e}")

    # 새로 크롤링
    print("🔄 새로운 청년공간 데이터 크롤링 중...")
    crawler = BusanYouthSpaceCrawler()
    spaces = crawler.crawl_all_spaces()

    # 캐시 저장
    cache_data = {
        'cached_at': datetime.now().isoformat(),
        'data': spaces
    }

    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print("청년공간 캐시 저장 완료")
    except Exception as e:
        print(f"캐시 저장 오류: {e}")

    return spaces


def search_spaces_by_region(region):
    """지역별 청년공간 검색"""
    spaces = get_youth_spaces_data()
    if not spaces:
        return "현재 청년공간 정보를 가져올 수 없습니다."

    # 정확한 지역 매칭 (부분 매칭 → 정확 매칭으로 변경)
    filtered_spaces = []
    for space in spaces:
        space_region = space.get('region', '').strip()
        if space_region == region:  # 정확히 일치하는 경우만
            filtered_spaces.append(space)

    if not filtered_spaces:
        return f"**{region}**에서 청년공간을 찾을 수 없습니다.\n\n다른 지역을 검색해보세요!"

    # 포맷 수정: 줄바꿈 제거
    result = f"**{region} 청년공간({len(filtered_spaces)}개)**\n\n"

    for space in filtered_spaces[:5]:  # 최대 5개만 표시
        result += format_space_info(space) + "\n"

    return result


def search_spaces_by_keyword(keyword):
    """키워드별 청년공간 검색"""
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

    for space in filtered_spaces[:5]:  # 최대 5개만 표시
        result += format_space_info(space) + "\n"

    return result


def format_space_info(space):
    """공간 정보 포맷팅 - 줄바꿈 제거"""
    # 포맷 수정: [지역]을 공간명 바로 뒤에 붙이기
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
    """전체 청년공간 목록"""
    spaces = get_youth_spaces_data()
    if not spaces:
        return "현재 청년공간 정보를 가져올 수 없습니다."

    result = f"**부산 청년공간 전체 목록** ({len(spaces)}개)\n\n"

    # 지역별로 그룹화
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
