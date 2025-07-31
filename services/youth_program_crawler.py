import requests
import re
import time
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime


class BusanYouthProgramCrawler:
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
        self.programs_data = []

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

    def extract_program_info_from_li(self, li_element):
        """li 요소에서 프로그램 정보 추출"""
        try:
            program_info = {
                'title': '',
                'region': '',
                'location': '',
                'status': '',
                'application_period': '',
                'link': '',
                'program_date': '',
                'description': ''
            }

            # 링크 추출
            link_element = li_element.select_one('a')
            if link_element:
                href = link_element.get('href', '')
                if href:
                    program_info['link'] = urljoin(self.base_url, href)

            # 모집 상태 확인 (모집중인 것만)
            recruit_state = li_element.select_one('.recruit_state .ing')
            if not recruit_state or recruit_state.get_text(strip=True) != '모집중':
                return None  # 모집중이 아니면 제외

            program_info['status'] = '모집중'

            # 제목 추출
            recruit_tit = li_element.select_one('.recruit_tit')
            if recruit_tit:
                title = recruit_tit.get_text(strip=True)
                program_info['title'] = title

                # 제목에서 지역 정보 추출 (예: [해운대구], [금정구])
                region_match = re.search(r'\[([^]]+구)\]', title)
                if region_match:
                    program_info['region'] = region_match.group(1)

            # 신청기간 추출
            recruit_date = li_element.select_one('.recruit_date')
            if recruit_date:
                date_spans = recruit_date.find_all('span')
                if len(date_spans) >= 2:
                    date_text = date_spans[1].get_text(strip=True)
                    program_info['application_period'] = date_text

            # 장소/기관 정보 추출 (part3에서)
            part3 = li_element.select_one('.part3')
            if part3:
                location_text = part3.get_text(strip=True)
                if location_text:
                    program_info['location'] = location_text

            # 최소 조건 확인 (제목과 모집중 상태가 있어야 함)
            if program_info['title'] and program_info['status'] == '모집중':
                return program_info
            else:
                return None

        except Exception as e:
            print(f"프로그램 정보 추출 오류: {e}")
            return None

    def extract_programs_from_page(self, soup):
        """페이지에서 프로그램 목록 추출"""
        programs = []

        # ul > li 구조에서 프로그램 추출
        program_list = soup.select('ul li')

        for li_element in program_list:
            try:
                # recruit_state가 있는 li만 처리 (프로그램 항목)
                if li_element.select_one('.recruit_state'):
                    program_info = self.extract_program_info_from_li(li_element)
                    if program_info:
                        programs.append(program_info)
            except Exception as e:
                continue

        return programs

    def has_program_content(self, soup):
        """페이지에 프로그램 콘텐츠가 있는지 확인"""
        if not soup:
            return False
        program_items = soup.select('.recruit_state')
        return len(program_items) > 0

    def crawl_all_programs(self):
        """모든 청년 프로그램 크롤링"""
        print("부산 청년 프로그램 크롤링 시작")
        all_programs = []

        # 여러 페이지 크롤링 시도
        for page in range(1, 6):  # 최대 5페이지까지
            print(f"페이지 {page} 크롤링 중...")

            if page == 1:
                url = "https://young.busan.go.kr/policySupport/act.nm?menuCd=261"
            else:
                # 다양한 페이지네이션 URL 시도
                possible_urls = [
                    f"https://young.busan.go.kr/policySupport/act.nm?menuCd=261&pageIndex={page}",
                    f"https://young.busan.go.kr/policySupport/act.nm?menuCd=261&page={page}",
                    f"https://young.busan.go.kr/policySupport/act.nm?menuCd=261&currentPage={page}",
                ]

                soup = None
                for url in possible_urls:
                    soup = self.get_page_content(url)
                    if soup and self.has_program_content(soup):
                        break
                    time.sleep(0.5)

                if not soup or not self.has_program_content(soup):
                    print(f"페이지 {page}에서 더 이상 프로그램을 찾을 수 없습니다.")
                    break

            if page == 1:
                soup = self.get_page_content(url)

            if not soup:
                continue

            page_programs = self.extract_programs_from_page(soup)
            if not page_programs:  # 프로그램이 없으면 종료
                print(f"페이지 {page}에서 프로그램을 찾을 수 없습니다.")
                break

            all_programs.extend(page_programs)
            print(f"페이지 {page}에서 {len(page_programs)}개 프로그램 수집")
            time.sleep(1)  # 페이지 간 지연

        print(f"크롤링 완료: {len(all_programs)}개 모집중인 프로그램 수집")
        self.programs_data = all_programs
        return all_programs


def get_youth_programs_data():
    """청년 프로그램 데이터 가져오기"""
    import os
    from datetime import datetime, timedelta

    cache_file = 'youth_programs_cache.json'
    cache_duration = timedelta(hours=6)  # 6시간 캐시 (프로그램은 더 자주 업데이트)

    # 캐시 파일 확인
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            cache_time = datetime.fromisoformat(cached_data['cached_at'])
            if datetime.now() - cache_time < cache_duration:
                print("캐시된 프로그램 데이터 사용")
                return cached_data['data']
        except:
            pass

    # 새로 크롤링
    print("🔄 새로운 프로그램 데이터 크롤링 중...")
    crawler = BusanYouthProgramCrawler()
    programs = crawler.crawl_all_programs()

    # 캐시 저장
    cache_data = {
        'cached_at': datetime.now().isoformat(),
        'data': programs
    }

    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print("프로그램 캐시 저장 완료")
    except:
        pass

    return programs


def search_programs_by_region(region):
    """지역별 청년 프로그램 검색"""
    programs = get_youth_programs_data()
    if not programs:
        return "현재 청년 프로그램 정보를 가져올 수 없습니다."

    # 지역명 정규화 (구 제거)
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

    if not filtered_programs:
        return f"**{region}**에서 현재 모집중인 청년 프로그램을 찾을 수 없습니다.\n\n다른 지역을 검색해보세요!"

    result = f"**{region} 청년 프로그램** ({len(filtered_programs)}개 모집중)\n\n"

    for program in filtered_programs[:8]:  # 최대 8개 표시
        result += format_program_info(program) + "\n"

    if len(filtered_programs) > 8:
        result += f"\n... 외 {len(filtered_programs) - 8}개 프로그램 더 있음"

    return result


def search_programs_by_keyword(keyword):
    """키워드별 청년 프로그램 검색"""
    programs = get_youth_programs_data()
    if not programs:
        return "현재 청년 프로그램 정보를 가져올 수 없습니다."

    filtered_programs = []
    keyword_lower = keyword.lower()

    for program in programs:
        if (keyword_lower in program.get('title', '').lower() or
                keyword_lower in program.get('location', '').lower() or
                keyword_lower in program.get('region', '').lower()):
            filtered_programs.append(program)

    if not filtered_programs:
        return f"**{keyword}** 관련 모집중인 청년 프로그램을 찾을 수 없습니다.\n\n다른 키워드로 검색해보세요!"

    result = f"🔍 **{keyword}** 검색 결과 ({len(filtered_programs)}개 모집중)\n\n"

    for program in filtered_programs[:8]:  # 최대 8개 표시
        result += format_program_info(program) + "\n"

    if len(filtered_programs) > 8:
        result += f"\n... 외 {len(filtered_programs) - 8}개 프로그램 더 있음"

    return result


def format_program_info(program):
    """프로그램 정보 포맷팅"""
    result = f"**{program['title']}**\n"

    if program.get('status'):
        status_emoji = "🟢" if program['status'] == '모집중' else "🔴"
        result += f"{status_emoji} {program['status']}\n"

    if program.get('application_period'):
        result += f"📅 신청기간: {program['application_period']}\n"

    if program.get('location'):
        result += f"📍 장소: {program['location']}\n"

    if program.get('region'):
        result += f"🏛️ 지역: {program['region']}\n"

    if program.get('link'):
        result += f"🔗 [자세히 보기]({program['link']})\n"

    return result


def get_all_youth_programs():
    """전체 모집중인 청년 프로그램 목록"""
    programs = get_youth_programs_data()
    if not programs:
        return "현재 청년 프로그램 정보를 가져올 수 없습니다."

    result = f"**부산 청년 프로그램 모집중** ({len(programs)}개)\n\n"

    # 지역별로 그룹화
    regions = {}
    for program in programs:
        region = program.get('region', '기타')
        if not region or region == '기타':
            # 제목에서 지역 추출 시도
            title = program.get('title', '')
            region_match = re.search(r'\[([^]]+구)\]', title)
            if region_match:
                region = region_match.group(1)
            else:
                region = '전체/기타'

        if region not in regions:
            regions[region] = []
        regions[region].append(program)

    for region, region_programs in sorted(regions.items()):
        result += f"**{region}** ({len(region_programs)}개)\n"
        for program in region_programs[:3]:  # 각 지역당 최대 3개
            result += f"{program['title']}\n"
            if program.get('application_period'):
                result += f"{program['application_period']}\n"

        if len(region_programs) > 3:
            result += f"     ... 외 {len(region_programs) - 3}개 더\n"
        result += "\n"

    result += "💡 지역명이나 프로그램명으로 자세한 정보를 검색해보세요!"
    return result


def get_programs_by_category():
    """카테고리별 프로그램 분류"""
    programs = get_youth_programs_data()
    if not programs:
        return "현재 청년 프로그램 정보를 가져올 수 없습니다."

    categories = {
        '취업/진로': [],
        '교육/강의': [],
        '창업': [],
        '문화/예술': [],
        '기타': []
    }

    for program in programs:
        title = program.get('title', '').lower()
        categorized = False

        if any(keyword in title for keyword in ['취업', 'job', '컨설팅', '면접', '이력서']):
            categories['취업/진로'].append(program)
            categorized = True
        elif any(keyword in title for keyword in ['교육', '강의', '과정', '교실', '스쿨']):
            categories['교육/강의'].append(program)
            categorized = True
        elif any(keyword in title for keyword in ['창업', '사업', '비즈니스']):
            categories['창업'].append(program)
            categorized = True
        elif any(keyword in title for keyword in ['문화', '예술', '공연', '전시', '음악', '미술']):
            categories['문화/예술'].append(program)
            categorized = True

        if not categorized:
            categories['기타'].append(program)

    result = "**카테고리별 청년 프로그램**\n\n"

    for category, category_programs in categories.items():
        if category_programs:
            result += f"**{category}** ({len(category_programs)}개)\n"
            for program in category_programs[:3]:
                result += f"{program['title']}\n"
            if len(category_programs) > 3:
                result += f"     ... 외 {len(category_programs) - 3}개 더\n"
            result += "\n"

    return result


# 테스트 함수
if __name__ == "__main__":
    # 크롤링 테스트
    crawler = BusanYouthProgramCrawler()
    programs = crawler.crawl_all_programs()

    print(f"\n총 {len(programs)}개 모집중인 프로그램 수집:")
    for i, program in enumerate(programs[:5], 1):
        print(f"\n{i}. {program['title']}")
        print(f"   상태: {program['status']}")
        print(f"   신청기간: {program['application_period']}")
        print(f"   장소: {program['location']}")
        if program['link']:
            print(f"   링크: {program['link']}")