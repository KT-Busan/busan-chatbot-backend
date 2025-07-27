import pandas as pd
from datetime import datetime, date
import re
from app import app, db, JobPosting


def find_header_row(filepath):
    """CSV 파일을 열어 실제 헤더가 시작되는 줄 번호를 찾기"""
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            for i, line in enumerate(f):
                # 헤더로 판단할 핵심 키워드가 모두 포함되어 있는지 확인
                if '모집 여부' in line and '제목' in line and '신청기간' in line:
                    print(f"헤더를 {i + 1}번째 줄에서 찾았습니다.")
                    return i  # 0부터 시작하는 줄 번호 반환
    except FileNotFoundError:
        return None
    return None


def parse_date(date_str):
    """다양한 날짜 형식을 파싱하여 date 객체로 변환하는 함수"""
    if not isinstance(date_str, str): return None
    match = re.search(r'(\d{4})[.-]?\s*(\d{1,2})[.-]?\s*(\d{1,2})', date_str)
    if match:
        try:
            year, month, day = map(int, match.groups())
            return date(year, month, day)
        except ValueError:
            return None
    return None


def import_csv_to_db(filepath):
    """
    CSV 파일을 읽어서 JobPosting 테이블의 모든 데이터를 삭제하고 새로 추가
    """
    with app.app_context():
        try:
            db.session.query(JobPosting).delete()
            db.session.commit()
            print("기존 일자리 데이터를 모두 삭제했습니다.")
        except Exception as e:
            db.session.rollback()
            print(f"데이터 삭제 중 오류 발생: {e}")
            return

        try:
            # 1. CSV 파일에서 헤더가 있는 줄을 먼저 찾기
            header_row = find_header_row(filepath)
            if header_row is None:
                print(f"오류: '{filepath}' 파일에서 헤더 행을 찾을 수 없습니다.")
                return

            # 2. 찾은 헤더 줄을 기준으로 CSV 파일을 읽기
            df = pd.read_csv(filepath, header=header_row, encoding='utf-8-sig')

            # 3. 컬럼 이름의 앞뒤 공백을 모두 제거
            df.columns = df.columns.str.strip()

            if '모집 여부' not in df.columns:
                print("오류: '모집 여부' 컬럼을 찾을 수 없습니다. 헤더가 잘못된 것 같습니다.")
                return

            new_postings = []
            today = date.today()

            for index, row in df.iterrows():
                status = str(row.get('모집 여부', '')).strip()
                if status == '모집중':
                    period = str(row.get('신청기간', ''))
                    end_date_str = period.split('~')[-1].strip()
                    end_date = parse_date(end_date_str)

                    if end_date and end_date >= today:
                        new_postings.append(JobPosting(
                            status=row.get('모집 여부'),
                            title=row.get('제목'),
                            period=period,
                            organization=row.get('담당기관'),
                            schedule=row.get('진행일정'),
                            phone=row.get('문의 전화'),
                            email=row.get('문의 이메일'),
                            target=row.get('지원대상'),
                            details=row.get('상세정보'),
                            link=row.get('URL'),
                            end_date=end_date
                        ))

            if new_postings:
                db.session.bulk_save_objects(new_postings)
                db.session.commit()
                print(f"총 {len(new_postings)}개의 새로운 '모집중'인 데이터를 추가했습니다.")
            else:
                print("추가할 '모집중'인 데이터가 없습니다. CSV 파일의 '모집 여부' 컬럼 내용과 신청기간을 확인해주세요.")

        except Exception as e:
            db.session.rollback()
            print(f"CSV 처리 중 오류 발생: {e}")


if __name__ == '__main__':
    csv_file_path = '부산_청년지원사업.csv'
    import_csv_to_db(csv_file_path)