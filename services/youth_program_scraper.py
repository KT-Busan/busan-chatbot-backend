import requests
import re
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime


class YouthProgramScraper:
    def __init__(self):
        self.base_url = "https://www.busanjob.net"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def scrape_youth_programs(self, max_programs=3):
        """청년 프로그램 목록 수집 (최대 max_programs개)"""
        try:
            url = "https://www.busanjob.net/03_part/part01_ddr.asp"
            response = self.session.get(url, timeout=10)
            response.encoding = 'euc-kr'
            soup = BeautifulSoup(response.content, 'html.parser')

            programs = []

            # 프로그램 목록이 있는 테이블 찾기
            tables = soup.find_all('table')

            for table in tables:
                rows = table.find_all('tr')

                for i, row in enumerate(rows):
                    if len(programs) >= max_programs:
                        break

                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        # 첫 번째 행이 헤더인지 확인
                        if i == 0 and any(keyword in cell.get_text() for cell in cells for keyword in
                                          ['번호', '제목', '분류', '등록일', '마감일', '상태']):
                            continue

                        program_info = self.extract_program_info_from_row(cells, url)
                        if program_info and program_info['title'] and len(program_info['title']) > 2:
                            # 중복 제거 (제목이 같은 프로그램 제외)
                            if not any(p['title'] == program_info['title'] for p in programs):
                                programs.append(program_info)

                if len(programs) >= max_programs:
                    break

            # 등록일 기준으로 정렬 (최신 순)
            programs_with_dates = []
            programs_without_dates = []

            for program in programs:
                register_date = self.parse_date(program.get('register_date', ''))
                if register_date:
                    program['register_date_obj'] = register_date
                    programs_with_dates.append(program)
                else:
                    programs_without_dates.append(program)

            # 등록일이 최신인 것을 우선으로 정렬
            programs_with_dates.sort(key=lambda x: x['register_date_obj'], reverse=True)

            return programs_with_dates + programs_without_dates

        except Exception as e:
            print(f"Error scraping youth programs: {str(e)}")
            return []

    def extract_program_info_from_row(self, cells, base_url):
        """테이블 행에서 프로그램 정보 추출"""
        try:
            program_info = {
                'title': '',
                'category': '',
                'status': '',
                'register_date': '',
                'deadline': '',
                'link': '',
                'details': ''
            }

            # 셀 내용 추출
            cell_texts = [cell.get_text(strip=True) for cell in cells]

            if len(cell_texts) >= 3:
                for i, text in enumerate(cell_texts):
                    if not text or text.isdigit():
                        continue

                    # 제목 찾기 (가장 긴 텍스트 또는 링크가 있는 텍스트)
                    if not program_info['title'] and len(text) > 3:
                        # 링크가 있는 셀에서 제목 추출
                        link_element = cells[i].find('a')
                        if link_element:
                            program_info['title'] = text
                            href = link_element.get('href')
                            if href:
                                if href.startswith('http'):
                                    program_info['link'] = href
                                else:
                                    program_info['link'] = urljoin(base_url, href)
                        elif len(text) > 5 and not program_info['title']:
                            program_info['title'] = text

                    # 상태 정보 찾기 (모집중, 마감, 진행중 등)
                    elif any(status in text for status in ['모집중', '마감', '진행중', '종료', '접수중']):
                        program_info['status'] = text

                    # 분류 정보 찾기
                    elif any(category in text for category in ['교육', '문화', '취업', '창업', '체험', '프로그램']):
                        if not program_info['category']:
                            program_info['category'] = text

                    # 날짜 정보 찾기
                    elif self.is_date_format(text):
                        if not program_info['register_date']:
                            program_info['register_date'] = text
                        elif not program_info['deadline']:
                            program_info['deadline'] = text

                # 세부 정보는 모든 셀의 텍스트 조합
                program_info['details'] = ' | '.join([t for t in cell_texts if t and not t.isdigit() and len(t) > 1])

                return program_info if program_info['title'] else None

        except Exception as e:
            print(f"Error extracting program info from row: {str(e)}")
            return None

    def is_date_format(self, text):
        """텍스트가 날짜 형식인지 확인"""
        if not text:
            return False
        return bool(re.search(r'\d{4}[-./]\d{1,2}[-./]\d{1,2}|\d{1,2}[-./]\d{1,2}|\d{4}년|\d{1,2}월', text))

    def parse_date(self, date_str):
        """날짜 문자열을 날짜 객체로 변환"""
        if not date_str:
            return None

        try:
            # 다양한 날짜 형식 처리
            date_patterns = [
                r'(\d{4})[-./](\d{1,2})[-./](\d{1,2})',
                r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일?',
                r'(\d{1,2})[-./](\d{1,2})'
            ]

            for pattern in date_patterns:
                match = re.search(pattern, date_str)
                if match:
                    groups = match.groups()
                    if len(groups) == 3:
                        year, month, day = groups
                        if len(year) == 2:
                            year = '20' + year
                        return datetime(int(year), int(month), int(day)).date()
                    elif len(groups) == 2:
                        month, day = groups
                        current_year = datetime.now().year
                        return datetime(current_year, int(month), int(day)).date()

            return None
        except:
            return None


def get_youth_programs():
    """청년 프로그램 정보를 가져와서 포맷팅"""
    try:
        scraper = YouthProgramScraper()
        programs = scraper.scrape_youth_programs(max_programs=3)

        if not programs:
            return "현재 청년 프로그램 정보를 가져올 수 없습니다. 잠시 후 다시 시도해주세요."

        result_text = "🎯 **부산 청년 프로그램** 최신 정보입니다!\n\n"

        for i, program in enumerate(programs, 1):
            result_text += f"**{i}. {program['title']}**\n"
            if program.get('category'):
                result_text += f"   - **분류:** {program['category']}\n"
            if program.get('status'):
                result_text += f"   - **상태:** {program['status']}\n"
            if program.get('register_date'):
                result_text += f"   - **등록일:** {program['register_date']}\n"
            if program.get('deadline'):
                result_text += f"   - **마감일:** {program['deadline']}\n"
            if program.get('link'):
                result_text += f"   - **상세보기:** [링크 바로가기]({program['link']})\n"
            result_text += "\n"

        result_text += "더 많은 청년 프로그램은 [부산잡 청년 프로그램 페이지](https://www.busanjob.net/03_part/part01_ddr.asp)에서 확인하실 수 있습니다."
        return result_text

    except Exception as e:
        print(f"청년 프로그램 크롤링 오류: {e}")
        return "죄송합니다. 현재 청년 프로그램 정보를 가져오는 데 문제가 발생했습니다. 직접 [부산잡 사이트](https://www.busanjob.net/03_part/part01_ddr.asp)를 방문해 주세요."