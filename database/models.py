import os
import pandas as pd
import re
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    anonymous_id = db.Column(db.String(120), unique=True, nullable=False)
    chats = db.relationship('Chat', backref='user', lazy=True, cascade="all, delete-orphan")


class Chat(db.Model):
    id = db.Column(db.String(120), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('Message', backref='chat', lazy=True, cascade="all, delete-orphan")


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(120), db.ForeignKey('chat.id'), nullable=False)
    sender = db.Column(db.String(50), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class JobPosting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(50))
    title = db.Column(db.Text, nullable=False)
    period = db.Column(db.String(100))
    organization = db.Column(db.Text)
    schedule = db.Column(db.Text)
    phone = db.Column(db.String(100))
    email = db.Column(db.String(100))
    target = db.Column(db.Text)
    details = db.Column(db.Text)
    link = db.Column(db.Text)
    end_date = db.Column(db.Date)


def initialize_database(app):
    """데이터베이스 초기화 및 CSV 데이터 로드"""
    with app.app_context():
        db.create_all()

        # JobPosting 테이블이 비어있는지 확인
        if JobPosting.query.first() is None:
            print("일자리 정보가 비어있어 CSV 파일로부터 데이터를 가져옵니다...")
            load_csv_data(app)


def find_header_row(filepath):
    """CSV 파일에서 헤더 행 찾기"""
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            for i, line in enumerate(f):
                if '모집 여부' in line and '제목' in line:
                    print(f"헤더를 {i + 1}번째 줄에서 찾았습니다.")
                    return i
    except Exception as e:
        print(f"헤더 검색 중 오류: {e}")
    return None


def parse_date(date_str):
    """날짜 문자열을 date 객체로 변환"""
    if not isinstance(date_str, str):
        return None
    matches = re.findall(r'(\d{4})-(\d{2})-(\d{2})', date_str)
    if matches:
        last_date = matches[-1]
        return datetime.strptime(f"{last_date[0]}-{last_date[1]}-{last_date[2]}", "%Y-%m-%d").date()
    return None


def load_csv_data(app):
    """CSV 파일에서 데이터 로드"""
    basedir = os.path.abspath(os.path.dirname(__file__))
    csv_file_path = os.path.join(os.path.dirname(basedir), '부산_청년지원사업.csv')
    print(f"CSV 파일 경로: {csv_file_path}")

    if not os.path.exists(csv_file_path):
        print(f"오류: '{csv_file_path}' 파일을 찾을 수 없습니다.")
        return

    try:
        header_row = find_header_row(csv_file_path)
        if header_row is None:
            print("오류: CSV 파일에서 헤더를 찾을 수 없습니다.")
            return

        df = pd.read_csv(csv_file_path, header=header_row, encoding='utf-8-sig')
        df.columns = df.columns.str.strip()

        if '모집 여부' not in df.columns:
            print(f"오류: CSV 파일에서 '모집 여부' 컬럼을 찾을 수 없습니다. 인식된 컬럼: {df.columns.tolist()}")
            return

        new_postings = []
        # '모집중'인 데이터만 필터링
        job_data = df[df['모집 여부'].str.strip() == '모집중'].copy()
        job_data.fillna('', inplace=True)  # NaN 값을 빈 문자열로 대체

        for _, row in job_data.iterrows():
            end_date = parse_date(row['신청기간'])
            new_post = JobPosting(
                status=row.get('모집 여부', '').strip(),
                title=row.get('제목', '').strip(),
                period=row.get('신청기간', '').strip(),
                organization=row.get('담당기관', '').strip(),
                schedule=row.get('진행일정', '').strip(),
                phone=row.get('문의 전화', '').strip(),
                email=row.get('문의 이메일', '').strip(),
                target=row.get('지원대상', '').strip(),
                details=row.get('상세정보', '').strip(),
                link=row.get('URL', '').strip(),
                end_date=end_date
            )
            new_postings.append(new_post)

        if new_postings:
            db.session.bulk_save_objects(new_postings)
            db.session.commit()
            print(f"총 {len(new_postings)}개의 일자리 데이터를 DB에 추가했습니다.")
        else:
            print("CSV 파일에서 추가할 '모집중'인 데이터가 없습니다.")

    except Exception as e:
        print(f"CSV 파일 처리 중 오류 발생: {e}")
        db.session.rollback()