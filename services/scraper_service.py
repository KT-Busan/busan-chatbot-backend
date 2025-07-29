import requests
import re
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime


class BusanJobScraper:
    def __init__(self):
        self.base_url = "https://busanjob.net"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_job_list_urls(self):
        """채용정보 페이지 URL들을 수집"""
        job_urls = [
            "/01_emif/emif01_1.asp?mbs=B",  # 구인정보 (기업채용)
            "/01_emif/emif01_1.asp?mbs=P",  # 구인정보 (공공채용)
        ]
        return [urljoin(self.base_url, url) for url in job_urls]

    def scrape_job_listings(self, url, job_type, max_jobs=5):
        """특정 채용 페이지에서 채용공고 목록 수집 (최대 max_jobs개)"""
        try:
            response = self.session.get(url, timeout=10)
            response.encoding = 'euc-kr'
            soup = BeautifulSoup(response.content, 'html.parser')

            jobs = []

            # 채용공고 테이블 찾기
            tables = soup.find_all('table')

            for table in tables:
                rows = table.find_all('tr')

                for i, row in enumerate(rows):
                    if len(jobs) >= max_jobs:  # 최대 개수 제한
                        break

                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        # 첫 번째 행이 헤더인지 확인
                        if i == 0 and any(keyword in cell.get_text() for cell in cells for keyword in
                                          ['번호', '제목', '회사', '등록일', '마감일']):
                            continue

                        job_info = self.extract_job_info_from_row(cells, job_type, url)
                        if job_info and job_info['title'] and len(job_info['title']) > 2:
                            jobs.append(job_info)

                if len(jobs) >= max_jobs:
                    break

            # 마감일 기준으로 정렬 (가까운 순서대로)
            jobs_with_dates = []
            jobs_without_dates = []

            for job in jobs:
                deadline_date = self.parse_deadline_date(job.get('deadline', ''))
                if deadline_date:
                    job['deadline_date'] = deadline_date
                    jobs_with_dates.append(job)
                else:
                    jobs_without_dates.append(job)

            # 마감일이 있는 것을 우선으로 정렬
            jobs_with_dates.sort(key=lambda x: x['deadline_date'])

            return jobs_with_dates + jobs_without_dates

        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return []

    def extract_job_info_from_row(self, cells, job_type, base_url):
        """테이블 행에서 채용정보 추출"""
        try:
            job_info = {
                'job_type': job_type,
                'company': '',
                'title': '',
                'location': '',
                'deadline': '',
                'register_date': '',
                'link': '',
                'details': ''
            }

            # 셀 내용 추출
            cell_texts = [cell.get_text(strip=True) for cell in cells]

            if len(cell_texts) >= 3:
                for i, text in enumerate(cell_texts):
                    if not text or text.isdigit():
                        continue

                    if not job_info['title'] and len(text) > 2:
                        job_info['title'] = text
                        # 제목에서 링크 찾기
                        link_element = cells[i].find('a')
                        if link_element and link_element.get('href'):
                            href = link_element['href']
                            if href.startswith('http'):
                                job_info['link'] = href
                            else:
                                job_info['link'] = urljoin(base_url, href)
                    elif not job_info['company'] and job_info['title'] and len(text) > 1:
                        job_info['company'] = text
                    elif self.is_date_format(text):
                        if not job_info['register_date']:
                            job_info['register_date'] = text
                        elif not job_info['deadline']:
                            job_info['deadline'] = text

                job_info['details'] = ' | '.join([t for t in cell_texts if t and not t.isdigit()])

                return job_info if job_info['title'] else None

        except Exception as e:
            print(f"Error extracting job info from row: {str(e)}")
            return None

    def is_date_format(self, text):
        """텍스트가 날짜 형식인지 확인"""
        if not text:
            return False
        return bool(re.search(r'\d{4}[-./]\d{1,2}[-./]\d{1,2}|\d{1,2}[-./]\d{1,2}|\d{4}년|\d{1,2}월', text))

    def parse_deadline_date(self, deadline_str):
        """마감일 문자열을 날짜 객체로 변환"""
        if not deadline_str:
            return None

        try:
            # 다양한 날짜 형식 처리
            date_patterns = [
                r'(\d{4})[-./](\d{1,2})[-./](\d{1,2})',
                r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일?',
                r'(\d{1,2})[-./](\d{1,2})'
            ]

            for pattern in date_patterns:
                match = re.search(pattern, deadline_str)
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

    def get_latest_jobs(self, max_jobs=3):
        """최신 채용공고를 마감일 순으로 가져오기"""
        all_jobs = []
        job_urls = self.get_job_list_urls()

        for url in job_urls:
            job_type = "기업채용" if "mbs=B" in url else "공공채용"
            jobs = self.scrape_job_listings(url, job_type, max_jobs)
            all_jobs.extend(jobs)
            time.sleep(1)  # 서버 부하 방지

        # 전체 결과에서 마감일 기준 정렬 후 상위 max_jobs개 반환
        jobs_with_dates = [job for job in all_jobs if job.get('deadline_date')]
        jobs_without_dates = [job for job in all_jobs if not job.get('deadline_date')]

        jobs_with_dates.sort(key=lambda x: x['deadline_date'])

        final_jobs = (jobs_with_dates + jobs_without_dates)[:max_jobs]
        return final_jobs


def get_busanjob_latest_jobs():
    """부산잡에서 최신 채용정보 3개를 가져와서 포맷팅"""
    try:
        scraper = BusanJobScraper()
        jobs = scraper.get_latest_jobs(max_jobs=3)

        if not jobs:
            return "현재 부산잡에서 채용정보를 가져올 수 없습니다. 잠시 후 다시 시도해주세요."

        result_text = "**Busan Jobs**에서 가져온 최신 채용정보 (마감 임박 순)입니다! 🔥\n\n"

        for i, job in enumerate(jobs, 1):
            result_text += f"**{i}. {job['title']}**\n"
            if job.get('company'):
                result_text += f"   - **회사:** {job['company']}\n"
            result_text += f"   - **유형:** {job['job_type']}\n"
            if job.get('deadline'):
                result_text += f"   - **마감일:** {job['deadline']}\n"
            if job.get('register_date'):
                result_text += f"   - **등록일:** {job['register_date']}\n"
            if job.get('link'):
                result_text += f"   - **상세보기:** [링크 바로가기]({job['link']})\n"
            result_text += "\n"

        result_text += "더 많은 채용정보는 [부산잡 홈페이지](https://busanjob.net)에서 확인하실 수 있습니다."
        return result_text

    except Exception as e:
        print(f"부산잡 크롤링 오류: {e}")
        return "죄송합니다. 현재 부산잡 사이트에서 정보를 가져오는 데 문제가 발생했습니다. 직접 [부산잡 사이트](https://busanjob.net)를 방문해 주세요."