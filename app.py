# app.py - 메인 실행 파일 (라우팅 전용)
import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from database.models import db, initialize_database
from handlers.chat_handler import chat_handler
from handlers.user_handler import user_handler
from handlers.program_handler import program_handler
from handlers.space_handler import space_handler

# --- 1. 기본 설정 ---
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(os.environ.get('RENDER_DISK_PATH', basedir), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

app = Flask(__name__)

# --- 2. 데이터베이스 설정 ---
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "chatbot.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


# --- 3. CORS 헤더 설정 ---
@app.after_request
def after_request(response):
    allowed_origins = [
        'http://localhost:5173',  # Vite 개발 서버
        'http://localhost:3000',  # Create React App 개발 서버
        'http://127.0.0.1:5173',  # 로컬 IP
        'http://127.0.0.1:3000',  # 로컬 IP
        'https://kt-busan.github.io'  # 프로덕션 배포
    ]
    origin = request.headers.get('Origin')
    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)

    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


# === 채팅 관련 API ===
@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    """채팅 요청 처리"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    data = request.get_json()
    user_message_text = data.get("message")
    anonymous_id = data.get("anonymousId")
    chat_id = data.get("chatId")

    result, status_code = chat_handler.process_chat_message(user_message_text, anonymous_id, chat_id)
    return jsonify(result), status_code


@app.route("/api/chat/<chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    """채팅 삭제"""
    result, status_code = chat_handler.delete_chat_session(chat_id)
    return jsonify(result), status_code


# === 사용자 관련 API ===
@app.route("/api/history/<anonymous_id>", methods=["GET"])
def get_history(anonymous_id):
    """사용자 채팅 히스토리 조회"""
    history = user_handler.get_user_history(anonymous_id)
    return jsonify(history)


@app.route("/api/user/<anonymous_id>", methods=["GET"])
def get_user(anonymous_id):
    """사용자 정보 조회"""
    result = user_handler.get_user_info(anonymous_id)
    return jsonify(result)


@app.route("/api/user", methods=["POST"])
def create_user():
    """사용자 생성"""
    data = request.get_json()
    anonymous_id = data.get('anonymous_id')
    result = user_handler.create_user(anonymous_id)
    return jsonify(result)


@app.route("/api/users/stats", methods=["GET"])
def get_users_stats():
    """사용자 통계"""
    result = user_handler.get_users_stats()
    return jsonify(result)


# === 프로그램 관련 API ===
@app.route('/api/programs', methods=['GET'])
def get_programs():
    """전체 프로그램 목록"""
    result = program_handler.get_all_programs()
    return jsonify(result)


@app.route('/api/programs/region/<region>', methods=['GET'])
def get_programs_by_region_api(region):
    """지역별 프로그램 검색"""
    result = program_handler.get_programs_by_region(region)
    return jsonify(result)


@app.route('/api/programs/crawl', methods=['POST'])
def crawl_programs_now():
    """수동 프로그램 크롤링"""
    result = program_handler.crawl_programs_manually()
    return jsonify(result)


@app.route('/api/programs/search', methods=['GET'])
def search_programs():
    """키워드별 프로그램 검색"""
    keyword = request.args.get('keyword', '')
    result = program_handler.search_programs_by_keyword(keyword)
    return jsonify(result)


# === 청년공간 관련 API ===
@app.route('/api/spaces', methods=['GET'])
def get_spaces():
    """전체 청년공간 목록"""
    result = space_handler.get_all_spaces()
    return jsonify(result)


@app.route('/api/spaces/region/<region>', methods=['GET'])
def get_spaces_by_region_api(region):
    """지역별 청년공간 검색"""
    result = space_handler.get_spaces_by_region(region)
    return jsonify(result)


@app.route('/api/spaces/search', methods=['GET'])
def search_spaces_api():
    """키워드별 청년공간 검색"""
    keyword = request.args.get('keyword', '')
    result = space_handler.search_spaces_by_keyword(keyword)
    return jsonify(result)


@app.route('/api/spaces/all', methods=['GET'])
def get_all_spaces_formatted():
    """전체 청년공간 목록 (포맷된)"""
    result = space_handler.get_all_spaces_formatted()
    return jsonify(result)


@app.route('/api/spaces/crawl', methods=['POST'])
def crawl_spaces_now():
    """수동 청년공간 크롤링"""
    result = space_handler.crawl_spaces_manually()
    return jsonify(result)


# === 청년공간 예약 관련 API (새로 추가) ===
@app.route('/api/spaces/filter-options', methods=['GET'])
def get_space_filter_options():
    """청년공간 검색 필터 옵션들 반환 (인원수, 구비물품, 구분)"""
    result = space_handler.get_filter_options()
    return jsonify(result)


@app.route('/api/spaces/reservation/search', methods=['POST'])
def search_spaces_for_reservation():
    """조건에 맞는 청년공간 검색 (예약용)"""
    data = request.get_json()
    capacity = data.get('capacity')
    equipment = data.get('equipment', [])
    space_type = data.get('type')

    result = space_handler.search_spaces_for_reservation(capacity, equipment, space_type)
    return jsonify(result)


@app.route('/api/spaces/detail/<space_name>', methods=['GET'])
def get_space_detail_api(space_name):
    """특정 공간의 상세 정보"""
    result = space_handler.get_space_detail(space_name)
    return jsonify(result)


# === 헬스체크 ===
@app.route('/health', methods=['GET'])
def health_check():
    """시스템 헬스체크"""
    from datetime import datetime
    return jsonify({
        'status': 'healthy',
        'service': 'busan-chatbot-backend',
        'timestamp': datetime.utcnow().isoformat(),
        'components': {
            'chat_handler': 'active',
            'user_handler': 'active',
            'program_handler': 'active',
            'space_handler': 'active',
            'database': 'connected'
        }
    })


# === 메인 실행 ===
if __name__ == "__main__":
    print("🚀 부산 챗봇 시작 (기능별 모듈 구조)...")
    initialize_database(app)
    print("✅ 모든 핸들러 준비 완료!")
    app.run(host='0.0.0.0', port=5001, debug=True)
else:
    initialize_database(app)