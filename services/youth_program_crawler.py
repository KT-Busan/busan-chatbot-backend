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
                    date_text = date_spans[1].get_text(strip=True)
                    program_info['application_period'] = date_text

            part3 = li_element.select_one('.part3')
            if part3:
                location_text = part3.get_text(strip=True)
                if location_text:
                    program_info['location'] = location_text

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

        program_list = soup.select('ul li')

        for li_element in program_list:
            try:
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

        for page in range(1, 6):
            print(f"페이지 {page} 크롤링 중...")

            if page == 1:
                url = "https://young.busan.go.kr/policySupport/act.nm?menuCd=261"
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
                    print(f"페이지 {page}에서 더 이상 프로그램을 찾을 수 없습니다.")
                    break

            if page == 1:
                soup = self.get_page_content(url)

            if not soup:
                continue

            page_programs = self.extract_programs_from_page(soup)
            if not page_programs:
                print(f"페이지 {page}에서 프로그램을 찾을 수 없습니다.")
                break

            all_programs.extend(page_programs)
            print(f"페이지 {page}에서 {len(page_programs)}개 프로그램 수집")
            time.sleep(1)  # 페이지 간 지연

        print(f"크롤링 완료: {len(all_programs)}개 모집중인 프로그램 수집")
        self.programs_data = all_programs
        return all_programs


def parse_deadline_date(application_period):
    """신청기간에서 마감일 추출 및 파싱"""
    try:
        if not application_period:
            return None

        import re
        date_pattern = r'(\d{4})[.-](\d{1,2})[.-](\d{1,2})'
        dates = re.findall(date_pattern, application_period)

        if len(dates) >= 2:
            year, month, day = dates[1]
            return datetime(int(year), int(month), int(day))
        elif len(dates) == 1:
            year, month, day = dates[0]
            return datetime(int(year), int(month), int(day))

        return None
    except:
        return None


def get_youth_programs_data():
    """청년 프로그램 데이터 가져오기"""
    import os
    from datetime import datetime, timedelta

    basedir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.dirname(basedir)
    instance_path = os.path.join(os.environ.get('RENDER_DISK_PATH', project_root), 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)

    cache_file = os.path.join(instance_path, 'youth_programs_cache.json')
    cache_duration = timedelta(hours=3)

    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            cache_time = datetime.fromisoformat(cached_data['cached_at'])
            if datetime.now() - cache_time < cache_duration:
                print("캐시된 프로그램 데이터 사용")
                return cached_data['data']
        except Exception as e:
            print(f"캐시 읽기 오류: {e}")

    print("🔄 새로운 프로그램 데이터 크롤링 중...")
    crawler = BusanYouthProgramCrawler()
    programs = crawler.crawl_all_programs()

    cache_data = {
        'cached_at': datetime.now().isoformat(),
        'data': programs
    }

    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print("프로그램 캐시 저장 완료")
    except Exception as e:
        print(f"캐시 저장 오류: {e}")

    return programs


def get_region_from_location(location, spaces_data=None):
    """장소명으로부터 지역 추출 - 개선된 버전"""
    if not location:
        return ""

    print(f"🔍 지역 매칭 시도: '{location}'")

    if spaces_data:
        for space in spaces_data:
            space_name = space.get('name', '').strip()

            if location.strip() == space_name:
                region = space.get('region', '')
                print(f"✅ 완전 일치 발견: '{location}' -> '{region}'")
                return region

            if (space_name in location or location in space_name) and len(space_name) > 3:
                region = space.get('region', '')
                print(f"✅ 부분 일치 발견: '{location}' <-> '{space_name}' -> '{region}'")
                return region

    location_mappings = {
        '해운대': '해운대구',
        '해운대 청년채움공간': '해운대구',
        '해운대 청년JOB카페': '해운대구',
        '해운대 청년잡카페': '해운대구',

        '고고씽': '남구',
        '청년창조발전소 고고씽 Job': '남구',
        '청년창조발전소  고고씽 Job': '남구',
        '청년창조발전소 고고씽': '남구',
        '동네 청년공간 공간숲': '남구',
        '공간숲': '남구',
        '남구': '남구',

        '꿈터': '금정구',
        '청년창조발전소 꿈터+': '금정구',
        '청년창조발전소   꿈터+': '금정구',
        '청년창조발전소 꿈터': '금정구',
        '금정': '금정구',
        '금정구': '금정구',

        '청년작당소': '중구',
        '청년문화교류공간': '중구',
        '청년문화교류공간 \'청년작당소\'': '중구',
        '청년문화교류공간 청년작당소': '중구',
        '부산청년센터': '중구',
        '오름라운지': '중구',
        '중구 청년센터': '중구',
        '중구': '중구',

        '부산진구': '부산진구',
        '와글와글플랫폼': '부산진구',
        '청년 FLEX': '부산진구',
        '부산진구청년플랫폼': '부산진구',
        '청년두드림센터': '부산진구',
        '청년창조발전소 디자인스프링': '부산진구',
        '디자인스프링': '부산진구',
        '청년마음건강센터': '부산진구',
        '부산청년잡': '부산진구',

        '동래': '동래구',
        '동래구': '동래구',
        '동래구 청년어울림센터': '동래구',

        '영도': '영도구',
        '영도구': '영도구',
        '다:이룸': '영도구',
        '청년희망플랫폼': '영도구',

        '북구': '북구',
        '서구': '서구',
        '동구': '동구',
        '사하': '사하구',
        '사하구': '사하구',
        '강서': '강서구',
        '강서구': '강서구',
        '연제': '연제구',
        '연제구': '연제구',
        '수영': '수영구',
        '수영구': '수영구',
        '사상': '사상구',
        '사상구': '사상구',
        '기장': '기장군',
        '기장군': '기장군'
    }

    location_clean = location.strip()
    if location_clean in location_mappings:
        region = location_mappings[location_clean]
        print(f"✅ 하드코딩 완전 일치: '{location}' -> '{region}'")
        return region

    sorted_mappings = sorted(location_mappings.items(), key=lambda x: len(x[0]), reverse=True)
    for keyword, region in sorted_mappings:
        if keyword in location and len(keyword) > 2:
            print(f"✅ 하드코딩 부분 일치: '{location}' 포함 '{keyword}' -> '{region}'")
            return region

    print(f"❌ 지역 매칭 실패: '{location}'")
    return ""


def search_programs_by_region(region):
    """지역별 청년 프로그램 검색 - 요구사항에 맞는 형식으로 수정"""
    programs = get_youth_programs_data()

    try:
        from services.youth_space_crawler import get_youth_spaces_data
        spaces_data = get_youth_spaces_data()
        print(f"📊 청년공간 데이터 로드: {len(spaces_data)}개")
    except Exception as e:
        print(f"청년공간 데이터 로드 실패: {e}")
        spaces_data = []

    if not programs:
        return f"📍 {region} 청년공간 프로그램 안내(마감 임박순)\n\n현재 프로그램 정보를 가져올 수 없습니다.\n\n📌 전체 프로그램은 [청년 공간 프로그램](https://young.busan.go.kr/policySupport/act.nm?menuCd=261)에서 더 확인할 수 있어요."

    print(f"🔍 '{region}' 지역 프로그램 검색 시작")
    print(f"📊 전체 프로그램: {len(programs)}개")

    # 지역 정규화
    if region.endswith('구') or region.endswith('군'):
        region_normalized = region[:-1]
    else:
        region_normalized = region

    print(f"🎯 정규화된 지역명: '{region_normalized}' (원본: '{region}')")

    # 프로그램 필터링 및 지역 매칭
    filtered_programs = []
    for i, program in enumerate(programs, 1):
        program_region = program.get('region', '')
        program_location = program.get('location', '')
        program_title = program.get('title', '')

        print(f"📋 프로그램 {i}: '{program_title[:50]}...' | 지역: '{program_region}' | 장소: '{program_location}'")

        match_found = False
        match_reason = ""

        # 1. 제목에서 지역 매칭
        if region_normalized in program_title or f"[{region}]" in program_title:
            match_found = True
            match_reason = "제목 매칭"
        # 2. 지역 필드에서 매칭
        elif region in program_region or region_normalized in program_region:
            match_found = True
            match_reason = "지역 필드 매칭"
        # 3. 장소명을 통한 지역 매칭
        else:
            location_region = get_region_from_location(program_location, spaces_data)
            if location_region and (region in location_region or region_normalized in location_region):
                match_found = True
                match_reason = f"장소 매칭 ({program_location} -> {location_region})"
                # 지역 정보 업데이트
                if not program_region:
                    program['region'] = location_region
                    print(f"  🔄 지역 정보 업데이트: '{location_region}'")

        if match_found:
            # 마감일 파싱 추가
            deadline = parse_deadline_date(program.get('application_period', ''))
            program['deadline_date'] = deadline
            filtered_programs.append(program)
            print(f"  ✅ {match_reason} - 프로그램 추가됨")
        else:
            print(f"  ❌ 매칭 실패")

    print(f"🎯 최종 결과: {len(filtered_programs)}개 프로그램")

    # 결과가 없는 경우
    if not filtered_programs:
        result = f"📍 {region} 청년공간 프로그램 안내(마감 임박순)\n\n"
        result += f"현재 **{region}**에서 모집중인 청년 공간 프로그램을 찾을 수 없습니다.\n\n"
        result += "다른 지역을 선택해보시거나, 전체 프로그램을 확인해보세요!\n\n"
        result += "📌 전체 프로그램은 [청년 공간 프로그램](https://young.busan.go.kr/policySupport/act.nm?menuCd=261)에서 더 확인할 수 있어요."
        return result

    # 마감일 기준으로 정렬 (마감 임박순)
    today = datetime.now()
    filtered_programs.sort(key=lambda x: (
        x['deadline_date'] is None,  # None 값은 뒤로
        x['deadline_date'] if x['deadline_date'] else datetime.max
    ))

    # 결과 포맷팅 - 요구사항에 맞는 형식
    result = f"📍 {region} 청년공간 프로그램 안내(마감 임박순)\n\n"

    # 최대 3개까지만 표시
    display_count = min(3, len(filtered_programs))

    for i, program in enumerate(filtered_programs[:display_count], 1):
        # 지역 정보 결정
        display_region = program.get('region', '')
        if not display_region:
            # region 필드가 비어있으면 요청된 지역 사용
            display_region = region

        # 프로그램명
        program_title = program.get('title', '프로그램명 없음')
        # 제목에서 지역 부분 제거 (중복 방지)
        if f"[{region}]" in program_title:
            program_title = program_title.replace(f"[{region}]", "").strip()
        if f"[{display_region}]" in program_title:
            program_title = program_title.replace(f"[{display_region}]", "").strip()

        # 장소명
        location = program.get('location', '장소 미정')

        # 신청기간
        application_period = program.get('application_period', '신청기간 미정')

        # 링크
        link = program.get('link', '')

        # 프로그램 정보 출력
        result += f"{i}️⃣ {display_region} {program_title}\n"
        result += f" • 장소: {location}\n"
        result += f"• 신청기간: {application_period}\n"

        if link:
            result += f"🔗 [자세히 보기]({link})\n"

        result += "\n"

    # 더 많은 프로그램이 있는 경우 안내
    if len(filtered_programs) > 3:
        result += f"... 외 {len(filtered_programs) - 3}개 프로그램 더 있음\n\n"

    # 전체 프로그램 링크
    result += "📌 전체 프로그램은 [청년 공간 프로그램](https://young.busan.go.kr/policySupport/act.nm?menuCd=261)에서 더 확인할 수 있어요."

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

    regions = {}
    for program in programs:
        region = program.get('region', '기타')
        if not region or region == '기타':
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
