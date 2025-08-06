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


def parse_deadline_date(application_period):
    """신청기간에서 마감일 추출 및 파싱"""
    try:
        if not application_period:
            return None

        # "2024.12.01 ~ 2024.12.31" 형태에서 마감일 추출
        import re
        date_pattern = r'(\d{4})[.-](\d{1,2})[.-](\d{1,2})'
        dates = re.findall(date_pattern, application_period)

        if len(dates) >= 2:
            # 마감일 (두 번째 날짜)
            year, month, day = dates[1]
            return datetime(int(year), int(month), int(day))
        elif len(dates) == 1:
            # 날짜가 하나만 있는 경우
            year, month, day = dates[0]
            return datetime(int(year), int(month), int(day))

        return None
    except:
        return None


def get_youth_programs_data():
    """청년 프로그램 데이터 가져오기"""
    import os
    from datetime import datetime, timedelta

    # 프로젝트 루트의 instance 폴더 경로 설정
    basedir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.dirname(basedir)  # services의 상위 폴더 (프로젝트 루트)
    instance_path = os.path.join(os.environ.get('RENDER_DISK_PATH', project_root), 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)

    cache_file = os.path.join(instance_path, 'youth_programs_cache.json')
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
        except Exception as e:
            print(f"캐시 읽기 오류: {e}")

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
    except Exception as e:
        print(f"캐시 저장 오류: {e}")

    return programs


def get_region_from_location(location, spaces_data=None):
    """장소명으로부터 지역 추출 - 개선된 버전"""
    if not location:
        return ""

    print(f"🔍 지역 매칭 시도: '{location}'")

    # 1. 청년공간 데이터에서 정확한 매칭 시도
    if spaces_data:
        for space in spaces_data:
            space_name = space.get('name', '').strip()

            # 완전 일치 확인
            if location.strip() == space_name:
                region = space.get('region', '')
                print(f"✅ 완전 일치 발견: '{location}' -> '{region}'")
                return region

            # 부분 일치 확인 (양방향)
            if (space_name in location or location in space_name) and len(space_name) > 3:
                region = space.get('region', '')
                print(f"✅ 부분 일치 발견: '{location}' <-> '{space_name}' -> '{region}'")
                return region

    # 2. 하드코딩된 매핑 (기존 + 추가)
    location_mappings = {
        # 해운대구
        '해운대': '해운대구',
        '해운대 청년채움공간': '해운대구',
        '해운대 청년JOB카페': '해운대구',
        '해운대 청년잡카페': '해운대구',

        # 남구
        '고고씽': '남구',
        '청년창조발전소 고고씽 Job': '남구',
        '청년창조발전소  고고씽 Job': '남구',  # 공백 2개
        '청년창조발전소 고고씽': '남구',
        '동네 청년공간 공간숲': '남구',
        '공간숲': '남구',
        '남구': '남구',

        # 금정구
        '꿈터': '금정구',
        '청년창조발전소 꿈터+': '금정구',
        '청년창조발전소   꿈터+': '금정구',  # 공백 3개
        '청년창조발전소 꿈터': '금정구',
        '금정': '금정구',
        '금정구': '금정구',

        # 중구
        '청년작당소': '중구',
        '청년문화교류공간': '중구',
        '청년문화교류공간 \'청년작당소\'': '중구',
        '청년문화교류공간 청년작당소': '중구',
        '부산청년센터': '중구',
        '오름라운지': '중구',
        '중구 청년센터': '중구',
        '중구': '중구',

        # 부산진구
        '부산진구': '부산진구',
        '와글와글플랫폼': '부산진구',
        '청년 FLEX': '부산진구',
        '부산진구청년플랫폼': '부산진구',
        '청년두드림센터': '부산진구',
        '청년창조발전소 디자인스프링': '부산진구',
        '디자인스프링': '부산진구',
        '청년마음건강센터': '부산진구',
        '부산청년잡': '부산진구',

        # 동래구
        '동래': '동래구',
        '동래구': '동래구',
        '동래구 청년어울림센터': '동래구',

        # 영도구
        '영도': '영도구',
        '영도구': '영도구',
        '다:이룸': '영도구',
        '청년희망플랫폼': '영도구',

        # 기타 지역들
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

    # 3. 완전 일치 우선 확인
    location_clean = location.strip()
    if location_clean in location_mappings:
        region = location_mappings[location_clean]
        print(f"✅ 하드코딩 완전 일치: '{location}' -> '{region}'")
        return region

    # 4. 부분 일치 확인 (긴 키워드부터)
    sorted_mappings = sorted(location_mappings.items(), key=lambda x: len(x[0]), reverse=True)
    for keyword, region in sorted_mappings:
        if keyword in location and len(keyword) > 2:  # 최소 3글자 이상만
            print(f"✅ 하드코딩 부분 일치: '{location}' 포함 '{keyword}' -> '{region}'")
            return region

    print(f"❌ 지역 매칭 실패: '{location}'")
    return ""


def search_programs_by_region(region):
    """지역별 청년 프로그램 검색 (수정된 버전)"""
    programs = get_youth_programs_data()

    # 청년공간 데이터도 가져오기 (지역 매칭용)
    try:
        from services.youth_space_crawler import get_youth_spaces_data
        spaces_data = get_youth_spaces_data()
        print(f"📊 청년공간 데이터 로드: {len(spaces_data)}개")
    except Exception as e:
        print(f"청년공간 데이터 로드 실패: {e}")
        spaces_data = []

    if not programs:
        return "현재 청년 프로그램 정보를 가져올 수 없습니다."

    print(f"🔍 '{region}' 지역 프로그램 검색 시작")
    print(f"📊 전체 프로그램: {len(programs)}개")

    # 정규화 로직 수정
    if region.endswith('구') or region.endswith('군'):
        region_normalized = region[:-1]  # 마지막 1글자만 제거
    else:
        region_normalized = region

    print(f"🎯 정규화된 지역명: '{region_normalized}' (원본: '{region}')")

    filtered_programs = []
    for i, program in enumerate(programs, 1):
        program_region = program.get('region', '')
        program_location = program.get('location', '')
        program_title = program.get('title', '')

        print(f"📋 프로그램 {i}: '{program_title[:50]}...' | 지역: '{program_region}' | 장소: '{program_location}'")

        match_found = False
        match_reason = ""

        # 1. 제목에서 지역 확인
        if region_normalized in program_title or f"[{region}]" in program_title:
            match_found = True
            match_reason = "제목 매칭"

        # 2. region 필드에서 지역 확인
        elif region in program_region or region_normalized in program_region:
            match_found = True
            match_reason = "지역 필드 매칭"

        # 3. location에서 지역 추출하여 확인 (가장 중요!)
        else:
            location_region = get_region_from_location(program_location, spaces_data)
            if location_region and (region in location_region or region_normalized in location_region):
                match_found = True
                match_reason = f"장소 매칭 ({program_location} -> {location_region})"

                # location에서 추출한 지역 정보로 업데이트
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

    if not filtered_programs:
        return f"**{region}**에서 현재 모집중인 청년 공간 프로그램을 찾을 수 없습니다.\n\n다른 지역을 검색해보세요!"

    # 마감일 임박 순으로 정렬 (마감일이 없는 것은 뒤로)
    today = datetime.now()
    filtered_programs.sort(key=lambda x: (
        x['deadline_date'] is None,  # None인 것들을 뒤로
        x['deadline_date'] if x['deadline_date'] else datetime.max  # 마감일 임박 순
    ))

    result = f"**{region} 청년 공간 프로그램** ({len(filtered_programs)}개 모집중)\n"
    result += "📅 *마감일 임박 순으로 정렬되었습니다*\n\n"

    for program in filtered_programs[:8]:  # 최대 8개만 표시
        # 마감일까지 남은 일수 계산
        deadline_info = ""
        if program.get('deadline_date'):
            days_left = (program['deadline_date'] - today).days
            if days_left < 0:
                deadline_info = " ⚠️ 마감"
            elif days_left <= 3:
                deadline_info = f" 🔥 D-{days_left}"
            elif days_left <= 7:
                deadline_info = f" ⏰ D-{days_left}"
            else:
                deadline_info = f" 📅 D-{days_left}"

        result += format_program_info(program, deadline_info) + "\n"

    if len(filtered_programs) > 8:
        result += f"... 외 {len(filtered_programs) - 8}개 프로그램 더 있음\n"

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
