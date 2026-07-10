import requests
import re
import time
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timedelta

# 데이터 출처: 부산청년플랫폼(young.busan.go.kr) 공개 페이지를 크롤링하여 수집.
# 저작권/출처는 부산광역시 및 부산청년플랫폼에 있으며, 본 서비스는 정보 안내 목적으로만 사용한다.


class BusanYouthProgramCrawler:
    def __init__(self):
        self.base_url = os.environ.get('CRAWLER_BASE_URL', 'https://young.busan.go.kr')
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
            response = self.session.get(url, timeout=15)
            response.encoding = encoding

            if response.status_code == 200:
                return BeautifulSoup(response.content, 'html.parser')
            return None
        except Exception:
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

            link_element = li_element.select_one('a')
            if link_element:
                href = link_element.get('href', '')
                if href:
                    program_info['link'] = urljoin(self.base_url, href)

            recruit_state = li_element.select_one('.recruit_state .ing')
            if not recruit_state or recruit_state.get_text(strip=True) != '모집중':
                return None
            program_info['status'] = '모집중'

            recruit_tit = li_element.select_one('.recruit_tit')
            if recruit_tit:
                title = recruit_tit.get_text(strip=True)
                program_info['title'] = title

                region_match = re.search(r'\[([^]]+구)\]', title)
                if region_match:
                    program_info['region'] = region_match.group(1)

            recruit_date = li_element.select_one('.recruit_date')
            if recruit_date:
                date_spans = recruit_date.find_all('span')
                if len(date_spans) >= 2:
                    program_info['application_period'] = date_spans[1].get_text(strip=True)

            part3 = li_element.select_one('.part3')
            if part3:
                location_text = part3.get_text(strip=True)
                if location_text:
                    program_info['location'] = location_text

            return program_info if program_info['title'] and program_info['status'] == '모집중' else None

        except Exception:
            return None

    def extract_programs_from_page(self, soup):
        """페이지에서 프로그램 목록 추출"""
        programs = []
        program_list = soup.select('ul li')

        for li_element in program_list:
            try:
                if li_element.select_one('.recruit_state'):
                    program_info = self.extract_program_info_from_li(li_element)
                    if program_info:
                        programs.append(program_info)
            except Exception:
                continue

        return programs

    def has_program_content(self, soup):
        """페이지에 프로그램 콘텐츠가 있는지 확인"""
        if not soup:
            return False
        return len(soup.select('.recruit_state')) > 0

    def crawl_all_programs(self):
        """모든 청년 프로그램 크롤링"""
        all_programs = []

        for page in range(1, 6):
            if page == 1:
                url = "https://young.busan.go.kr/policySupport/act.nm?menuCd=261"
                soup = self.get_page_content(url)
            else:
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
                    break

            if not soup:
                continue

            page_programs = self.extract_programs_from_page(soup)
            if not page_programs:
                break

            all_programs.extend(page_programs)
            time.sleep(1)

        self.programs_data = all_programs
        return all_programs


LOCATION_MAPPINGS = {
    '해운대': '해운대구', '해운대 청년채움공간': '해운대구', '해운대 청년JOB카페': '해운대구', '해운대 청년잡카페': '해운대구',
    '고고씽': '남구', '청년창조발전소 고고씽 Job': '남구', '청년창조발전소  고고씽 Job': '남구',
    '청년창조발전소 고고씽': '남구', '동네 청년공간 공간숲': '남구', '공간숲': '남구', '남구': '남구',
    '꿈터': '금정구', '청년창조발전소 꿈터+': '금정구', '청년창조발전소   꿈터+': '금정구',
    '청년창조발전소 꿈터': '금정구', '금정': '금정구', '금정구': '금정구',
    '청년작당소': '중구', '청년문화교류공간': '중구', '청년문화교류공간 \'청년작당소\'': '중구',
    '청년문화교류공간 청년작당소': '중구', '부산청년센터': '중구', '오름라운지': '중구',
    '중구 청년센터': '중구', '중구': '중구',
    '부산진구': '부산진구', '와글와글플랫폼': '부산진구', '청년 FLEX': '부산진구',
    '부산진구청년플랫폼': '부산진구', '청년두드림센터': '부산진구',
    '청년창조발전소 디자인스프링': '부산진구', '디자인스프링': '부산진구',
    '청년마음건강센터': '부산진구', '부산청년잡': '부산진구',
    '동래': '동래구', '동래구': '동래구', '동래구 청년어울림센터': '동래구',
    '영도': '영도구', '영도구': '영도구', '다:이룸': '영도구', '청년희망플랫폼': '영도구',
    '북구': '북구', '서구': '서구', '동구': '동구', '사하': '사하구', '사하구': '사하구',
    '강서': '강서구', '강서구': '강서구', '연제': '연제구', '연제구': '연제구',
    '수영': '수영구', '수영구': '수영구', '사상': '사상구', '사상구': '사상구',
    '기장': '기장군', '기장군': '기장군'
}


def parse_deadline_date(application_period):
    """신청기간에서 마감일 추출 및 파싱"""
    try:
        if not application_period:
            return None

        date_pattern = r'(\d{4})[.-](\d{1,2})[.-](\d{1,2})'
        dates = re.findall(date_pattern, application_period)

        if len(dates) >= 2:
            year, month, day = dates[1]
            return datetime(int(year), int(month), int(day))
        elif len(dates) == 1:
            year, month, day = dates[0]
            return datetime(int(year), int(month), int(day))

        return None
    except Exception:
        return None


def get_region_from_location(location, spaces_data=None):
    """장소명으로부터 지역 추출"""
    if not location:
        return ""

    if spaces_data:
        for space in spaces_data:
            space_name = space.get('name', '').strip()

            if location.strip() == space_name:
                return space.get('region', '')

            if (space_name in location or location in space_name) and len(space_name) > 3:
                return space.get('region', '')

    location_clean = location.strip()
    if location_clean in LOCATION_MAPPINGS:
        return LOCATION_MAPPINGS[location_clean]

    sorted_mappings = sorted(LOCATION_MAPPINGS.items(), key=lambda x: len(x[0]), reverse=True)
    for keyword, region in sorted_mappings:
        if keyword in location and len(keyword) > 2:
            return region

    return ""


def get_config_path():
    """config 경로 반환"""
    basedir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.dirname(basedir)
    config_path = os.path.join(project_root, 'config')
    os.makedirs(config_path, exist_ok=True)
    return config_path


def get_cache_file_path():
    """캐시 파일 경로 반환 - config 폴더만 사용"""
    config_file = os.path.join(get_config_path(), 'youth_programs_cache.json')
    return config_file


def refresh_programs_cache():
    """크롤링을 실행하고 config에 저장 (서버 부팅 시 / 관리자 강제 갱신 시에만 호출)"""
    crawler = BusanYouthProgramCrawler()
    programs = crawler.crawl_all_programs()

    cache_data = {
        'cached_at': datetime.now().isoformat(),
        'data': programs
    }

    try:
        with open(get_cache_file_path(), 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return programs


def is_programs_cache_stale(hours=3):
    """프로그램 캐시가 없거나 오래됐는지 확인"""
    cache_file = get_cache_file_path()
    if not os.path.exists(cache_file):
        return True
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cached_data = json.load(f)
        cache_time = datetime.fromisoformat(cached_data['cached_at'])
        return datetime.now() - cache_time >= timedelta(hours=hours)
    except Exception:
        return True


def ensure_programs_cache_fresh():
    """서버 부팅 시 1회 호출 - 캐시가 없거나 오래됐을 때만 크롤링을 실행해 채워둔다"""
    if is_programs_cache_stale():
        print("🔄 청년 프로그램 캐시가 오래되어 부팅 시점에 크롤링을 실행합니다...")
        refresh_programs_cache()
    else:
        print("✅ 청년 프로그램 캐시가 최신 상태입니다. 부팅 시 크롤링을 건너뜁니다.")


def get_youth_programs_data():
    """청년 프로그램 데이터 가져오기 (요청 시점 크롤링 없음, 캐시 파일만 사용)"""
    cache_file = get_cache_file_path()

    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            return cached_data.get('data', [])
        except Exception:
            return []
    return []


def normalize_region(region):
    """지역명 정규화"""
    if region.endswith('구') or region.endswith('군'):
        return region[:-1]
    return region


def match_program_region(program, region, region_normalized, spaces_data):
    """프로그램과 지역 매칭 검사"""
    program_region = program.get('region', '')
    program_location = program.get('location', '')
    program_title = program.get('title', '')

    if region_normalized in program_title or f"[{region}]" in program_title:
        return True

    if region in program_region or region_normalized in program_region:
        return True

    location_region = get_region_from_location(program_location, spaces_data)
    if location_region and (region in location_region or region_normalized in location_region):
        if not program_region:
            program['region'] = location_region
        return True

    return False


def format_program_list(programs, region, max_count=3):
    """프로그램 목록 포맷팅"""
    if not programs:
        return (f"📌\u00A0\u00A0{region} 청년공간 프로그램 안내(마감 임박순)\n\n"
                f"현재 {region}에서 모집중인 청년 공간 프로그램을 찾을 수 없습니다.\n"
                "다른 지역을 선택해보시거나, 전체 프로그램을 확인해보세요!\n\n"
                "📌\u00A0\u00A0전체 프로그램은 [청년 공간 프로그램](https://young.busan.go.kr/policySupport/act.nm?menuCd=261)에서 더 확인할 수 있어요.")

    programs.sort(key=lambda x: (
        x['deadline_date'] is None,
        x['deadline_date'] if x['deadline_date'] else datetime.max
    ))

    result = f"📌\u00A0\u00A0{region} 청년공간 프로그램 안내(마감 임박순)\n\n"

    display_count = min(3, len(programs))

    for i, program in enumerate(programs[:display_count], 1):
        display_region = program.get('region', '') or region

        program_title = program.get('title', '프로그램명 없음')
        for region_tag in [f"[{region}]", f"[{display_region}]"]:
            program_title = program_title.replace(region_tag, "").strip()

        result += f"{i}.\u00A0\u00A0{display_region} {program_title}\n"
        result += f"\u00A0\u00A0📍 장소 : {program.get('location', '장소 미정')}\n"
        result += f"\u00A0\u00A0📅 신청기간 : {program.get('application_period', '신청기간 미정')}\n"
        result += f"\u00A0\u00A0🔗 [자세히 보기]({program['link']})\n" if program.get('link') else "🔗 자세히 보기\n"

        if i < display_count:
            result += "---\n"

    result += "\n📌\u00A0\u00A0전체 프로그램은 [청년 공간 프로그램](https://young.busan.go.kr/policySupport/act.nm?menuCd=261)에서 더 확인할 수 있어요."
    return result


def search_programs_by_region(region):
    """지역별 청년 프로그램 검색"""
    programs = get_youth_programs_data()

    try:
        from services.youth_space_crawler import get_youth_spaces_data
        spaces_data = get_youth_spaces_data()
    except Exception:
        spaces_data = []

    if not programs:
        return f"📌 {region} 청년공간 프로그램 안내(마감 임박순)\n\n현재 프로그램 정보를 가져올 수 없습니다.\n\n📌 전체 프로그램은 [청년 공간 프로그램](https://young.busan.go.kr/policySupport/act.nm?menuCd=261)에서 더 확인할 수 있어요."

    region_normalized = normalize_region(region)
    filtered_programs = []

    for program in programs:
        if match_program_region(program, region, region_normalized, spaces_data):
            deadline = parse_deadline_date(program.get('application_period', ''))
            program['deadline_date'] = deadline
            filtered_programs.append(program)

    return format_program_list(filtered_programs, region)


def search_programs_by_keyword(keyword):
    """키워드별 청년 프로그램 검색"""
    programs = get_youth_programs_data()
    if not programs:
        return "현재 청년 프로그램 정보를 가져올 수 없습니다."

    keyword_lower = keyword.lower()
    filtered_programs = [
        program for program in programs
        if any(keyword_lower in str(program.get(field, '')).lower()
               for field in ['title', 'location', 'region'])
    ]

    if not filtered_programs:
        return f"{keyword} 관련 모집중인 청년 프로그램을 찾을 수 없습니다.\n\n다른 키워드로 검색해보세요!"

    result = f"🔍 {keyword} 검색 결과 ({len(filtered_programs)}개 모집중)\n\n"

    for program in filtered_programs[:8]:
        result += format_program_info(program) + "\n"

    if len(filtered_programs) > 8:
        result += f"\n... 외 {len(filtered_programs) - 8}개 프로그램 더 있음"

    return result


def format_program_info(program, deadline_info=""):
    """프로그램 정보 포맷팅"""
    result = f"**{program['title']}**{deadline_info}\n"

    if program.get('status'):
        status_emoji = "🟢" if program['status'] == '모집중' else "🔴"
        result += f"{status_emoji} {program['status']}\n"

    if program.get('application_period'):
        result += f"📅 신청기간 : {program['application_period']}\n"

    if program.get('location'):
        result += f"📍 장소 : {program['location']}\n"

    if program.get('region'):
        result += f"🏛️ 지역 : {program['region']}\n"

    if program.get('link'):
        result += f"🔗 [자세히 보기]({program['link']})\n"

    return result


def get_all_youth_programs():
    """전체 모집중인 청년 프로그램 목록"""
    programs = get_youth_programs_data()
    if not programs:
        return "현재 청년 프로그램 정보를 가져올 수 없습니다."

    result = f"**부산 청년 프로그램 모집중** ({len(programs)}개)\n\n"

    regions = {}
    for program in programs:
        region = program.get('region', '기타')
        if not region or region == '기타':
            title = program.get('title', '')
            region_match = re.search(r'\[([^]]+구)\]', title)
            region = region_match.group(1) if region_match else '전체/기타'

        regions.setdefault(region, []).append(program)

    for region, region_programs in sorted(regions.items()):
        result += f"{region} ({len(region_programs)}개)\n"
        for program in region_programs[:3]:
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
        '취업/진로': ['취업', 'job', '컨설팅', '면접', '이력서'],
        '교육/강의': ['교육', '강의', '과정', '교실', '스쿨'],
        '창업': ['창업', '사업', '비즈니스'],
        '문화/예술': ['문화', '예술', '공연', '전시', '음악', '미술'],
        '기타': []
    }

    categorized_programs = {category: [] for category in categories}

    for program in programs:
        title = program.get('title', '').lower()
        categorized = False

        for category, keywords in categories.items():
            if category != '기타' and any(keyword in title for keyword in keywords):
                categorized_programs[category].append(program)
                categorized = True
                break

        if not categorized:
            categorized_programs['기타'].append(program)

    result = "**카테고리별 청년 프로그램**\n\n"

    for category, category_programs in categorized_programs.items():
        if category_programs:
            result += f"**{category}** ({len(category_programs)}개)\n"
            for program in category_programs[:3]:
                result += f"{program['title']}\n"
            if len(category_programs) > 3:
                result += f"     ... 외 {len(category_programs) - 3}개 더\n"
            result += "\n"

    return result