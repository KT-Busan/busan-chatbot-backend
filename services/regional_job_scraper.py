import requests
import re
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
from datetime import datetime


class RegionalJobScraper:
    def __init__(self):
        self.base_url = "https://busanjob.net"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_region_jobs(self, region, job_type="기업", max_jobs=3):
        """특정 지역의 채용공고를 수집"""
        try:
            # URL 구성 - job_type에 따라 다른 URL 사용
            if job_type == "공공":
                search_url = f"https://busanjob.net/01_emif/emif01_1.asp?keyword={quote(region)}&region="
            else:  # 기업 채용
                search_url = f"https://busanjob.net/01_emif/emif01.asp?keyword={quote(region)}&region="

            response = self.session.get(search_url, timeout=10)
            response.encoding = 'euc-kr'
            soup = BeautifulSoup(response.content, 'html.parser')

            jobs = []

            # 채용공고 테이블 찾기
            tables = soup.find_all('table')

            for table in tables:
                rows = table.find_all('tr')

                for i, row in enumerate(rows):
                    if len(jobs) >= max_jobs:
                        break

                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 4:  # 최소 4개 컬럼 (번호, 제목, 회사, 기타 정보)
                        # 첫 번째 행이 헤더인지 확인
                        if i == 0 and any(keyword in cell.get_text() for cell in cells for keyword in
                                          ['번호', '제목', '회사', '등록일', '마감일', '구분']):
                            continue

                        job_info = self.extract_job_info_from_row(cells, search_url, region)
                        if job_info and job_info['title'] and len(job_info['title']) > 2:
                            # 현재 모집 중인 공고만 필터링하고 지역명이 포함된 채용공고만 필터링
                            if self.is_currently_recruiting(job_info) and (
                                    region in job_info['title'] or
                                    region in job_info.get('company', '') or
                                    region in job_info.get('location', '')
                            ):
                                job_info['job_type'] = job_type  # job_type 정보 추가
                                jobs.append(job_info)

                if len(jobs) >= max_jobs:
                    break

            # 등록일 기준으로 정렬 (최신 순)
            jobs_with_dates = []
            jobs_without_dates = []

            for job in jobs:
                register_date = self.parse_date(job.get('register_date', ''))
                if register_date:
                    job['register_date_obj'] = register_date
                    jobs_with_dates.append(job)
                else:
                    jobs_without_dates.append(job)

            # 등록일이 최신인 것을 우선으로 정렬
            jobs_with_dates.sort(key=lambda x: x['register_date_obj'], reverse=True)

            final_jobs = (jobs_with_dates + jobs_without_dates)[:max_jobs]

            # 결과가 부족하면 일반 채용공고도 포함
            if len(final_jobs) < max_jobs:
                general_jobs = self.get_general_jobs(max_jobs - len(final_jobs), job_type)
                final_jobs.extend(general_jobs)

            return final_jobs[:max_jobs]

        except Exception as e:
            print(f"Error scraping regional jobs for {region}: {str(e)}")
            return []

    def get_general_jobs(self, max_jobs=3, job_type="기업"):
        """일반 채용공고 수집 (지역 검색 결과가 부족할 때 사용)"""
        try:
            # job_type에 따라 다른 URL 사용
            if job_type == "공공":
                url = "https://busanjob.net/01_emif/emif01_1.asp"
            else:  # 기업 채용
                url = "https://busanjob.net/01_emif/emif01.asp"

            response = self.session.get(url, timeout=10)
            response.encoding = 'euc-kr'
            soup = BeautifulSoup(response.content, 'html.parser')

            jobs = []
            tables = soup.find_all('table')

            for table in tables:
                rows = table.find_all('tr')

                for i, row in enumerate(rows):
                    if len(jobs) >= max_jobs:
                        break

                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 4:
                        if i == 0:  # 헤더 스킵
                            continue

                        job_info = self.extract_job_info_from_row(cells, url)
                        if job_info and job_info['title'] and len(job_info['title']) > 2:
                            # 현재 모집 중인 공고만 필터링
                            if self.is_currently_recruiting(job_info):
                                job_info['job_type'] = job_type  # job_type 정보 추가
                                jobs.append(job_info)

                if len(jobs) >= max_jobs:
                    break

            return jobs

        except Exception as e:
            print(f"Error scraping general jobs: {str(e)}")
            return []

    def extract_job_info_from_row(self, cells, base_url, region=None):
        """테이블 행에서 채용정보 추출"""
        try:
            job_info = {
                'title': '',
                'company': '',
                'location': '',
                'job_type': '',
                'deadline': '',
                'register_date': '',
                'link': '',
                'details': '',
                'region': region or ''
            }

            # 셀 내용 추출
            cell_texts = [cell.get_text(strip=True) for cell in cells]

            if len(cell_texts) >= 3:
                for i, text in enumerate(cell_texts):
                    if not text or text.isdigit():
                        continue

                    # 제목 찾기 (링크가 있는 셀에서 우선 추출)
                    if not job_info['title'] and len(text) > 3:
                        link_element = cells[i].find('a')
                        if link_element:
                            job_info['title'] = text
                            href = link_element.get('href')
                            if href:
                                if href.startswith('http'):
                                    job_info['link'] = href
                                else:
                                    job_info['link'] = urljoin(base_url, href)
                        elif len(text) > 5 and not job_info['title']:
                            job_info['title'] = text

                    # 회사명 찾기
                    elif not job_info['company'] and job_info['title'] and len(text) > 1:
                        if text != job_info['title'] and not self.is_date_format(text):
                            job_info['company'] = text

                    # 날짜 정보 찾기
                    elif self.is_date_format(text):
                        if not job_info['register_date']:
                            job_info['register_date'] = text
                        elif not job_info['deadline']:
                            job_info['deadline'] = text

                    # 위치 정보 찾기 (부산 지역명 포함)
                    elif any(area in text for area in ['구', '군', '부산', '해운대', '강서', '기장']):
                        if not job_info['location']:
                            job_info['location'] = text

                # 세부 정보는 모든 셀의 텍스트 조합
                job_info['details'] = ' | '.join([t for t in cell_texts if t and not t.isdigit() and len(t) > 1])

                return job_info if job_info['title'] else None

        except Exception as e:
            print(f"Error extracting job info from row: {str(e)}")
            return None

    def parse_date(self, date_str):
        """날짜 파싱 함수 (수정됨)"""
        if not date_str:
            return None

        try:
            # 다양한 날짜 형식 처리
            date_patterns = [
                r'(\d{4})[-./](\d{1,2})[-./](\d{1,2})',
                r'(\d{2})[-./](\d{1,2})[-./](\d{1,2})',
                r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일?',
                r'(\d{1,2})[-./](\d{1,2})'
            ]

            for pattern in date_patterns:
                match = re.search(pattern, date_str)
                if match:
                    groups = match.groups()
                    if len(groups) == 3:
                        year, month, day = groups
                        # 2자리 연도를 4자리로 변환
                        if len(year) == 2:
                            if int(year) >= 25:  # 25년 이상이면 2025년 이후
                                year = '20' + year
                            else:
                                year = '20' + year
                        return datetime(int(year), int(month), int(day)).date()
                    elif len(groups) == 2:
                        month, day = groups
                        current_year = datetime.now().year
                        return datetime(current_year, int(month), int(day)).date()

            return None
        except Exception as e:
            print(f"날짜 파싱 오류: {e} - 입력값: {date_str}")
            return None

    def is_date_format(self, text):
        """텍스트가 날짜 형식인지 확인 (수정됨)"""
        if not text:
            return False
        return bool(re.search(
            r'\d{4}[-./]\d{1,2}[-./]\d{1,2}|\d{2}[-./]\d{1,2}[-./]\d{1,2}|\d{1,2}[-./]\d{1,2}|\d{4}년|\d{1,2}월', text))

    def is_currently_recruiting(self, job_info):
        """현재 모집 중인 공고인지 확인"""
        from datetime import date

        # 마감일이 있으면 현재 날짜와 비교
        if job_info.get('deadline'):
            deadline_date = self.parse_date(job_info['deadline'])
            if deadline_date:
                return deadline_date >= date.today()

        # 제목에서 모집 상태 확인
        title = job_info.get('title', '').lower()
        if any(keyword in title for keyword in ['마감', '종료', '완료']):
            return False

        # 모집중, 접수중 등의 키워드가 있으면 모집 중
        if any(keyword in title for keyword in ['모집중', '접수중', '채용중', 'recruiting']):
            return True

        # 등록일이 30일 이내면 현재 모집 중으로 간주
        if job_info.get('register_date'):
            register_date = self.parse_date(job_info['register_date'])
            if register_date:
                from datetime import timedelta
                return (date.today() - register_date).days <= 30

        # 기본적으로 모집 중으로 간주 (최신 정보일 가능성)
        return True

    def extract_overseas_job_info(self, cells, base_url, country=None):
        """해외 채용 테이블 행에서 채용정보 추출 (개선된 버전)"""
        try:
            job_info = {
                'title': '',
                'company': '',
                'location': '',
                'job_type': '',
                'deadline': '',
                'register_date': '',
                'link': '',
                'details': '',
                'country': country or ''
            }

            # 셀 내용 추출
            cell_texts = [cell.get_text(strip=True) for cell in cells]

            if len(cell_texts) >= 3:
                # 제목과 링크 찾기 (첫 번째 우선순위)
                for i, cell in enumerate(cells):
                    link_element = cell.find('a')
                    if link_element and not job_info['title']:
                        title_text = cell.get_text(strip=True)
                        if len(title_text) > 3:
                            job_info['title'] = title_text
                            href = link_element.get('href')
                            if href:
                                if href.startswith('http'):
                                    job_info['link'] = href
                                else:
                                    job_info['link'] = urljoin(base_url, href)
                            break

                # 나머지 정보 추출
                for i, text in enumerate(cell_texts):
                    if not text or text.isdigit() or text == job_info.get('title', ''):
                        continue

                    # 회사명 찾기
                    if not job_info['company'] and job_info['title'] and len(text) > 1:
                        if not self.is_date_format(text) and not any(
                                keyword in text.lower() for keyword in ['마감', '모집', '채용']):
                            job_info['company'] = text

                    # 날짜 정보 찾기
                    elif self.is_date_format(text):
                        if '~' in text or '마감' in text or 'deadline' in text.lower():
                            job_info['deadline'] = text
                        elif not job_info['register_date']:
                            job_info['register_date'] = text

                    # 국가/위치 정보 찾기 (우선순위: 입력된 국가명 포함)
                    elif country and country.lower() in text.lower():
                        job_info['country'] = text
                    elif any(keyword in text.lower() for keyword in
                             ['미국', '일본', '중국', '베트남', '싱가포르', '말레이시아', 'usa', 'japan', 'china', 'vietnam', 'singapore',
                              'malaysia']):
                        if not job_info['location']:
                            job_info['location'] = text

                    # 직종 정보 찾기 (더 포괄적)
                    elif any(keyword in text.lower() for keyword in
                             ['개발자', '엔지니어', '매니저', '디자이너', '마케팅', '영업', '관리', '교사', '간호사', '요리사', 'developer',
                              'engineer', 'manager', 'designer']):
                        if not job_info['job_type']:
                            job_info['job_type'] = text

                # 국가 정보가 없으면 입력된 국가명 사용
                if not job_info['country'] and not job_info['location']:
                    job_info['country'] = country

                # 세부 정보는 중요한 셀들만 조합
                important_texts = [t for t in cell_texts if
                                   t and not t.isdigit() and len(t) > 1 and t != job_info.get('title', '')]
                job_info['details'] = ' | '.join(important_texts[:3])  # 처음 3개만

                return job_info if job_info['title'] else None

        except Exception as e:
            print(f"Error extracting overseas job info from row: {str(e)}")
            return None

    def extract_overseas_job_from_table(self, cells, base_url, target_country):
        """부산잡 해외채용 테이블에서 정보 추출 (공고명/기관명, 국가, 직종, 마감일)"""
        try:
            if len(cells) < 4:
                return None

            # 각 셀에서 정보 추출
            title_cell = cells[0]  # 공고명/기관명
            country_cell = cells[1]  # 국가
            job_type_cell = cells[2]  # 직종
            deadline_cell = cells[3]  # 마감일

            # 기본 정보 추출
            title = title_cell.get_text(strip=True)
            country = country_cell.get_text(strip=True)
            job_type = job_type_cell.get_text(strip=True)
            deadline = deadline_cell.get_text(strip=True)

            # 링크 추출 (보통 제목 셀에 있음)
            link = base_url
            link_element = title_cell.find('a')
            if link_element and link_element.get('href'):
                href = link_element['href']
                if href.startswith('http'):
                    link = href
                else:
                    link = urljoin(base_url, href)

            # 유효한 데이터인지 확인
            if not title or len(title) < 3:
                return None

            job_info = {
                'title': title,
                'country': country,
                'job_type': job_type,
                'deadline': deadline,
                'link': link
            }

            print(f"📋 추출된 채용정보: {title} | {country} | {job_type} | {deadline}")
            return job_info

        except Exception as e:
            print(f"테이블 정보 추출 오류: {e}")
            return None

    def is_target_country_job(self, job_info, target_country):
        """해당 국가의 채용공고인지 확인"""
        target_lower = target_country.lower()

        # 제목에서 확인
        title = job_info.get('title', '').lower()
        if target_lower in title:
            return True

        # 국가 필드에서 확인
        country = job_info.get('country', '').lower()
        if target_lower in country:
            return True

        # 영어-한국어 매핑 확인
        country_mapping = {
            '일본': ['japan', 'japanese', '일본'],
            '미국': ['usa', 'america', 'american', '미국'],
            '중국': ['china', 'chinese', '중국'],
            '독일': ['germany', 'german', '독일'],
            '베트남': ['vietnam', 'vietnamese', '베트남'],
            '싱가포르': ['singapore', '싱가포르'],
            '말레이시아': ['malaysia', '말레이시아'],
            '캐나다': ['canada', '캐나다'],
            '호주': ['australia', '호주'],
            '폴란드': ['poland', 'polish', '폴란드'],
            '인도': ['india', 'indian', '인도'],
            '태국': ['thailand', 'thai', '태국']
        }

        if target_lower in country_mapping:
            keywords = country_mapping[target_lower]
            for keyword in keywords:
                if keyword in title or keyword in country:
                    return True

        return False

    def get_overseas_jobs_with_keyword(self, country):
        """키워드 검색으로 해외 채용정보 수집"""
        try:
            url = f"https://busanjob.net/01_emif/emif01_2.asp?keyword={quote(country)}"
            response = self.session.get(url, timeout=10)
            response.encoding = 'euc-kr'
            soup = BeautifulSoup(response.content, 'html.parser')

            jobs = []

            # 테이블에서 정보 추출 시도
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                        if self.contains_country_simple(row_text, country):
                            job_info = self.extract_job_from_row_text(cells, url)
                            if job_info:
                                jobs.append(job_info)
                                if len(jobs) >= 3:
                                    return jobs

            return jobs
        except Exception as e:
            print(f"키워드 검색 크롤링 오류: {e}")
            return []

    def get_overseas_jobs_from_text(self, country):
        """페이지 전체 텍스트에서 관련 정보 추출"""
        try:
            url = "https://busanjob.net/01_emif/emif01_2.asp"
            response = self.session.get(url, timeout=10)
            response.encoding = 'euc-kr'

            # 페이지에 국가명이 포함되어 있는지 확인
            content = response.text
            if country not in content and country.lower() not in content.lower():
                return []

            # 기본 채용정보 생성 (실제 크롤링이 어려울 때의 대안)
            jobs = [
                {
                    'title': f'{country} 현지 기업 채용',
                    'job_type': '다양한 직종',
                    'deadline': '상시 모집',
                    'link': url,
                    'period': '수시'
                },
                {
                    'title': f'{country} 한국계 기업 채용',
                    'job_type': '관리직, 기술직',
                    'deadline': '채용시까지',
                    'link': url,
                    'period': '연중'
                }
            ]

            return jobs
        except Exception as e:
            print(f"텍스트 추출 오류: {e}")
            return []

    def contains_country_simple(self, text, country):
        """텍스트에 해당 국가명이 포함되어 있는지 간단히 확인"""
        text_lower = text.lower()
        country_lower = country.lower()

        # 직접 매칭
        if country_lower in text_lower:
            return True

        # 영어-한국어 매핑
        country_maps = {
            '일본': ['japan', 'japanese'],
            '미국': ['usa', 'america', 'american'],
            '중국': ['china', 'chinese'],
            '독일': ['germany', 'german'],
            '베트남': ['vietnam', 'vietnamese'],
            '싱가포르': ['singapore'],
            '말레이시아': ['malaysia'],
            '캐나다': ['canada'],
            '호주': ['australia', 'australian']
        }

        if country_lower in country_maps:
            for keyword in country_maps[country_lower]:
                if keyword in text_lower:
                    return True

        return False

    def extract_job_type_from_text(self, text):
        """텍스트에서 직종 정보 추출"""
        job_keywords = [
            '개발자', '엔지니어', '매니저', '디자이너', '마케팅', '영업',
            '관리', '교사', '간호사', '요리사', '기술자', '상담원',
            'developer', 'engineer', 'manager', 'designer', 'marketing'
        ]

        text_lower = text.lower()
        for keyword in job_keywords:
            if keyword in text_lower:
                return keyword

        return '다양한 직종'

    def extract_date_from_text(self, text):
        """텍스트에서 날짜 정보 추출"""
        import re

        # 날짜 패턴 찾기
        date_patterns = [
            r'\d{4}[-./]\d{1,2}[-./]\d{1,2}',
            r'\d{1,2}[-./]\d{1,2}',
            r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일?'
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group()

        # 상대적 표현 찾기
        if any(keyword in text for keyword in ['상시', '수시', '채용시까지', '연중']):
            return '상시 모집'

        return '채용시까지'

    def extract_job_from_row_text(self, cells, base_url):
        """행 데이터에서 채용정보 추출"""
        try:
            cell_texts = [cell.get_text(strip=True) for cell in cells if cell.get_text(strip=True)]

            if len(cell_texts) < 2:
                return None

            # 가장 긴 텍스트를 제목으로 사용
            title = max(cell_texts, key=len) if cell_texts else ''

            # 링크 찾기
            link = base_url
            for cell in cells:
                link_element = cell.find('a')
                if link_element and link_element.get('href'):
                    link = urljoin(base_url, link_element['href'])
                    break

            return {
                'title': title,
                'job_type': self.extract_job_type_from_text(title),
                'deadline': self.extract_date_from_text(' '.join(cell_texts)),
                'link': link,
                'period': ''
            }
        except Exception as e:
            print(f"행 정보 추출 오류: {e}")
            return None

    def contains_country(self, job_info, target_country):
        """채용공고가 대상 국가와 관련이 있는지 확인"""
        target_lower = target_country.lower()

        # 제목에서 국가명 확인
        title = job_info.get('title', '').lower()
        if target_lower in title:
            return True

        # 국가 필드에서 확인
        country = job_info.get('country', '').lower()
        if target_lower in country:
            return True

        # 영어-한국어 매핑 확인
        country_mapping = {
            '일본': ['japan', 'japanese', '일본'],
            '미국': ['usa', 'america', 'american', '미국'],
            '중국': ['china', 'chinese', '중국'],
            '독일': ['germany', 'german', '독일'],
            '베트남': ['vietnam', 'vietnamese', '베트남'],
            '싱가포르': ['singapore', '싱가포르'],
            '말레이시아': ['malaysia', '말레이시아'],
            '캐나다': ['canada', '캐나다'],
            '호주': ['australia', '호주']
        }

        if target_lower in country_mapping:
            keywords = country_mapping[target_lower]
            for keyword in keywords:
                if keyword in title or keyword in country:
                    return True

        return False


def get_regional_jobs(region, job_type="기업"):
    """지역별 채용정보를 가져와서 포맷팅"""
    try:
        scraper = RegionalJobScraper()
        jobs = scraper.get_region_jobs(region, job_type, max_jobs=3)

        if not jobs:
            return f"현재 **{region}**에서 모집 중인 **{job_type} 채용** 정보를 찾을 수 없습니다.\n\n더 많은 채용정보는 [부산잡 채용정보](https://busanjob.net/01_emif/emif01.asp)에서 확인해주세요."

        result_text = f"📍 **{region} {job_type} 채용정보** (현재 모집 중인 상위 3개)입니다!\n\n"

        for i, job in enumerate(jobs, 1):
            result_text += f"**{i}. {job['title']}**\n"
            if job.get('company'):
                result_text += f"   - **회사:** {job['company']}\n"
            if job.get('location'):
                result_text += f"   - **위치:** {job['location']}\n"
            if job.get('register_date'):
                result_text += f"   - **등록일:** {job['register_date']}\n"
            if job.get('deadline'):
                result_text += f"   - **마감일:** {job['deadline']}\n"
            if job.get('link'):
                result_text += f"   - **상세보기:** [링크 바로가기]({job['link']})\n"
            result_text += "\n"

        result_text += f"더 많은 {region} 채용정보는 [부산잡 채용정보](https://busanjob.net/01_emif/emif01.asp?keyword={region})에서 확인하실 수 있습니다."
        return result_text

    except Exception as e:
        print(f"지역별 채용정보 크롤링 오류: {e}")
        return f"죄송합니다. 현재 **{region} {job_type} 채용** 정보를 가져오는 데 문제가 발생했습니다. 직접 [부산잡 사이트](https://busanjob.net/01_emif/emif01.asp)를 방문해 주세요."


def get_overseas_jobs(country):
    """해외 채용정보를 가져와서 포맷팅 - 부산잡 테이블 구조 기반"""
    try:
        scraper = RegionalJobScraper()

        # 부산잡 해외채용 페이지 접속
        url = "https://busanjob.net/01_emif/emif01_2.asp"
        response = scraper.session.get(url, timeout=10)
        response.encoding = 'euc-kr'
        soup = BeautifulSoup(response.content, 'html.parser')

        jobs = []

        # 채용정보 테이블 찾기 (공고명/기관명, 국가, 직종, 마감일 구조)
        tables = soup.find_all('table')

        for table in tables:
            rows = table.find_all('tr')

            # 헤더 행 찾기
            header_found = False
            for i, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 4:
                    header_text = ' '.join([cell.get_text(strip=True) for cell in cells])

                    # 테이블 헤더 확인 (공고명, 국가, 직종, 마감일)
                    if any(keyword in header_text for keyword in ['공고명', '기관명', '국가', '직종', '마감일']):
                        header_found = True
                        print(f"✅ 해외채용 테이블 헤더 발견: {header_text}")

                        # 헤더 다음 행들부터 데이터 추출
                        for j in range(i + 1, len(rows)):
                            data_row = rows[j]
                            data_cells = data_row.find_all(['td', 'th'])

                            if len(data_cells) >= 4:
                                job_info = scraper.extract_overseas_job_from_table(data_cells, url, country)
                                if job_info:
                                    jobs.append(job_info)
                        break

            if header_found:
                break

        # 입력한 국가와 관련된 채용공고만 필터링
        filtered_jobs = []
        for job in jobs:
            if scraper.is_target_country_job(job, country):
                filtered_jobs.append(job)

        # 마감일 기준으로 정렬 (가까운 순)
        from datetime import date
        today = date.today()

        current_jobs = []
        for job in filtered_jobs:
            deadline_date = scraper.parse_date(job.get('deadline', ''))
            if deadline_date and deadline_date >= today:
                job['deadline_date_obj'] = deadline_date
                current_jobs.append(job)
            elif not deadline_date:  # 마감일 정보가 없으면 포함
                current_jobs.append(job)

        # 마감일 순 정렬
        jobs_with_deadline = [job for job in current_jobs if job.get('deadline_date_obj')]
        jobs_without_deadline = [job for job in current_jobs if not job.get('deadline_date_obj')]

        jobs_with_deadline.sort(key=lambda x: x['deadline_date_obj'])
        final_jobs = (jobs_with_deadline + jobs_without_deadline)[:3]

        if not final_jobs:
            return f"현재 **{country}**에서 모집 중인 해외 채용 정보를 찾을 수 없습니다.\n\n더 많은 해외 채용정보는 [부산잡 해외채용](https://busanjob.net/01_emif/emif01_2.asp)에서 확인해주세요."

        result_text = f"🌍 **{country} 해외 채용정보** (마감 임박 순 {len(final_jobs)}개)입니다!\n\n"

        for i, job in enumerate(final_jobs, 1):
            result_text += f"**{i}. {job['title']}**\n"
            if job.get('job_type'):
                result_text += f"   - **직종:** {job['job_type']}\n"
            if job.get('deadline'):
                result_text += f"   - **마감일:** {job['deadline']}\n"
            if job.get('link'):
                result_text += f"   - **상세보기:** [링크 바로가기]({job['link']})\n"
            result_text += "\n"

        result_text += f"더 많은 {country} 해외 채용정보는 [부산잡 해외채용](https://busanjob.net/01_emif/emif01_2.asp)에서 확인하실 수 있습니다."
        return result_text

    except Exception as e:
        print(f"해외 채용정보 크롤링 오류: {e}")
        import traceback
        traceback.print_exc()
        return f"죄송합니다. 현재 **{country} 해외 채용** 정보를 가져오는 데 문제가 발생했습니다. 직접 [부산잡 해외채용](https://busanjob.net/01_emif/emif01_2.asp)을 방문해 주세요."