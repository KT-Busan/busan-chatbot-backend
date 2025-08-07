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
    """채팅 요청 처리 - 조건별 검색과 랜덤 추천 포함"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    try:
        print(f"📨 받은 요청 데이터: {request.get_json()}")

        data = request.get_json()

        if not data:
            print("❌ 요청 데이터가 없음")
            return jsonify({"error": "요청 데이터가 없습니다."}), 400

        user_message_text = data.get("message")
        anonymous_id = data.get("anonymousId")
        chat_id = data.get("chatId")

        print(f"📝 파싱된 데이터:")
        print(f"  - message: {user_message_text}")
        print(f"  - anonymousId: {anonymous_id}")
        print(f"  - chatId: {chat_id}")

        if not all([user_message_text, anonymous_id, chat_id]):
            missing_fields = []
            if not user_message_text: missing_fields.append("message")
            if not anonymous_id: missing_fields.append("anonymousId")
            if not chat_id: missing_fields.append("chatId")

            error_msg = f"필수 정보가 누락되었습니다: {', '.join(missing_fields)}"
            print(f"❌ {error_msg}")
            return jsonify({"error": error_msg}), 400

        print(f"✅ 모든 필수 데이터 확인됨, chat_handler 호출 시작")

        result, status_code = chat_handler.process_chat_message(
            user_message_text,
            anonymous_id,
            chat_id
        )

        print(f"✅ chat_handler 응답: {status_code}")
        return jsonify(result), status_code

    except Exception as e:
        print(f"❌ 채팅 처리 중 예외 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "서버 오류가 발생했습니다."}), 500


@app.route("/api/chat/<chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    """채팅 삭제"""
    try:
        result, status_code = chat_handler.delete_chat_session(chat_id)
        return jsonify(result), status_code
    except Exception as e:
        print(f"채팅 삭제 중 오류: {e}")
        return jsonify({"error": "서버 오류가 발생했습니다."}), 500


# === 사용자 관련 API ===
@app.route("/api/history/<anonymous_id>", methods=["GET"])
def get_history(anonymous_id):
    """사용자 채팅 히스토리 조회"""
    try:
        history = user_handler.get_user_history(anonymous_id)
        return jsonify(history)
    except Exception as e:
        print(f"히스토리 조회 오류: {e}")
        return jsonify({"error": "히스토리를 불러올 수 없습니다."}), 500


@app.route("/api/user/<anonymous_id>", methods=["GET"])
def get_user(anonymous_id):
    """사용자 정보 조회"""
    try:
        result = user_handler.get_user_info(anonymous_id)
        return jsonify(result)
    except Exception as e:
        print(f"사용자 정보 조회 오류: {e}")
        return jsonify({"error": "사용자 정보를 불러올 수 없습니다."}), 500


@app.route("/api/user", methods=["POST"])
def create_user():
    """사용자 생성"""
    try:
        data = request.get_json()
        anonymous_id = data.get('anonymous_id')
        result = user_handler.create_user(anonymous_id)
        return jsonify(result)
    except Exception as e:
        print(f"사용자 생성 오류: {e}")
        return jsonify({"error": "사용자 생성에 실패했습니다."}), 500


@app.route("/api/users/stats", methods=["GET"])
def get_users_stats():
    """사용자 통계"""
    try:
        result = user_handler.get_users_stats()
        return jsonify(result)
    except Exception as e:
        print(f"사용자 통계 조회 오류: {e}")
        return jsonify({"error": "통계 정보를 불러올 수 없습니다."}), 500


# === 프로그램 관련 API ===
@app.route('/api/programs', methods=['GET'])
def get_programs():
    """전체 프로그램 목록"""
    try:
        result = program_handler.get_all_programs()
        return jsonify(result)
    except Exception as e:
        print(f"프로그램 목록 조회 오류: {e}")
        return jsonify({"error": "프로그램 목록을 불러올 수 없습니다."}), 500


@app.route('/api/programs/region/<region>', methods=['GET'])
def get_programs_by_region_api(region):
    """지역별 프로그램 검색"""
    try:
        result = program_handler.get_programs_by_region(region)
        return jsonify(result)
    except Exception as e:
        print(f"지역별 프로그램 검색 오류: {e}")
        return jsonify({"error": f"{region} 지역 프로그램을 불러올 수 없습니다."}), 500


@app.route('/api/programs/crawl', methods=['POST'])
def crawl_programs_now():
    """수동 프로그램 크롤링"""
    try:
        result = program_handler.crawl_programs_manually()
        return jsonify(result)
    except Exception as e:
        print(f"프로그램 크롤링 오류: {e}")
        return jsonify({"error": "프로그램 크롤링에 실패했습니다."}), 500


@app.route('/api/programs/search', methods=['GET'])
def search_programs():
    """키워드별 프로그램 검색"""
    try:
        keyword = request.args.get('keyword', '')
        result = program_handler.search_programs_by_keyword(keyword)
        return jsonify(result)
    except Exception as e:
        print(f"프로그램 키워드 검색 오류: {e}")
        return jsonify({"error": "프로그램 검색에 실패했습니다."}), 500


# === 청년공간 관련 API ===
@app.route('/api/spaces', methods=['GET'])
def get_spaces():
    """전체 청년공간 목록"""
    try:
        result = space_handler.get_all_spaces()
        return jsonify(result)
    except Exception as e:
        print(f"청년공간 목록 조회 오류: {e}")
        return jsonify({"error": "청년공간 목록을 불러올 수 없습니다."}), 500


@app.route('/api/spaces/region/<region>', methods=['GET'])
def get_spaces_by_region_api(region):
    """지역별 청년공간 검색"""
    try:
        result = space_handler.get_spaces_by_region(region)
        return jsonify(result)
    except Exception as e:
        print(f"지역별 청년공간 검색 오류: {e}")
        return jsonify({"error": f"{region} 지역 청년공간을 불러올 수 없습니다."}), 500


@app.route('/api/spaces/search', methods=['GET'])
def search_spaces_api():
    """키워드별 청년공간 검색"""
    try:
        keyword = request.args.get('keyword', '')
        result = space_handler.search_spaces_by_keyword(keyword)
        return jsonify(result)
    except Exception as e:
        print(f"청년공간 키워드 검색 오류: {e}")
        return jsonify({"error": "청년공간 검색에 실패했습니다."}), 500


@app.route('/api/spaces/all', methods=['GET'])
def get_all_spaces_formatted():
    """전체 청년공간 목록 (포맷된)"""
    try:
        result = space_handler.get_all_spaces_formatted()
        return jsonify(result)
    except Exception as e:
        print(f"포맷된 청년공간 목록 조회 오류: {e}")
        return jsonify({"error": "청년공간 목록을 불러올 수 없습니다."}), 500


@app.route('/api/spaces/crawl', methods=['POST'])
def crawl_spaces_now():
    """수동 청년공간 크롤링"""
    try:
        result = space_handler.crawl_spaces_manually()
        return jsonify(result)
    except Exception as e:
        print(f"청년공간 크롤링 오류: {e}")
        return jsonify({"error": "청년공간 크롤링에 실패했습니다."}), 500


@app.route('/api/spaces/detail/<space_name>', methods=['GET'])
def get_space_detail_api(space_name):
    """특정 공간의 상세 정보"""
    try:
        result = space_handler.get_space_detail(space_name)
        return jsonify(result)
    except Exception as e:
        print(f"청년공간 상세 정보 조회 오류: {e}")
        return jsonify({"error": f"{space_name} 공간 정보를 불러올 수 없습니다."}), 500


# === 청년공간 상세 관련 API ===
@app.route('/api/spaces/busan-youth', methods=['GET'])
def get_busan_youth_spaces():
    """
    spaces_busan_youth.json 데이터 직접 반환
    - 조건별 검색 기능의 전체 공간 보기 모드에서 사용
    - chat_handler에서 이미 로드된 데이터 활용
    """
    try:
        spaces_data = chat_handler.spaces_data

        if not spaces_data:
            print("⚠️ spaces_busan_youth.json 데이터가 비어있습니다.")
            return jsonify({
                'success': False,
                'data': [],
                'count': 0,
                'message': '청년공간 데이터가 없습니다. JSON 파일을 확인해주세요.'
            }), 404

        print(f"✅ spaces_busan_youth.json에서 {len(spaces_data)}개 데이터 반환")
        return jsonify({
            'success': True,
            'data': spaces_data,
            'count': len(spaces_data),
            'message': f'{len(spaces_data)}개의 청년공간 데이터를 반환했습니다.'
        })

    except Exception as e:
        print(f"❌ 부산 청년공간 데이터 API 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': [],
            'count': 0,
            'message': '청년공간 데이터를 가져오는 중 오류가 발생했습니다.'
        }), 500


@app.route('/api/debug/spaces-status', methods=['GET'])
def get_spaces_debug_status():
    """청년공간 데이터 로딩 상태 디버깅"""
    try:
        from handlers.chat_handler import chat_handler

        # 데이터 상태 확인
        spaces_count = len(chat_handler.spaces_data) if chat_handler.spaces_data else 0

        # 파일 시스템 정보
        basedir = os.path.abspath(os.path.dirname(__file__))
        possible_paths = [
            os.path.join(basedir, 'config', 'spaces_busan_youth.json'),
            os.path.join(os.path.dirname(basedir), 'config', 'spaces_busan_youth.json'),
            '/app/config/spaces_busan_youth.json',
            os.path.join(os.environ.get('RENDER_DISK_PATH', ''), 'config', 'spaces_busan_youth.json')
        ]

        path_status = {}
        for path in possible_paths:
            path_status[path] = {
                'exists': os.path.exists(path),
                'readable': os.path.exists(path) and os.access(path, os.R_OK) if os.path.exists(path) else False
            }

        return jsonify({
            'success': True,
            'spaces_loaded': spaces_count,
            'file_paths': path_status,
            'current_dir': os.getcwd(),
            'app_dir': basedir,
            'render_path': os.environ.get('RENDER_DISK_PATH', 'None'),
            'sample_space': chat_handler.spaces_data[0] if chat_handler.spaces_data else None
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/debug/reload-spaces', methods=['POST'])
def reload_spaces_data():
    """청년공간 데이터 강제 재로드"""
    try:
        from handlers.chat_handler import chat_handler

        old_count = len(chat_handler.spaces_data)
        chat_handler.spaces_data = chat_handler.load_spaces_data()
        new_count = len(chat_handler.spaces_data)

        return jsonify({
            'success': True,
            'message': f'데이터 재로드 완료: {old_count} → {new_count}개',
            'old_count': old_count,
            'new_count': new_count
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# === 헬스체크 ===
@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health_check():
    """시스템 헬스체크"""
    try:
        from datetime import datetime

        spaces_count = len(chat_handler.spaces_data) if chat_handler.spaces_data else 0

        return jsonify({
            'status': 'healthy',
            'service': 'busan-chatbot-backend',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'chat_handler': 'active',
                'user_handler': 'active',
                'program_handler': 'active',
                'space_handler': 'active',
                'database': 'connected',
                'spaces_data': f'{spaces_count} spaces loaded'
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'service': 'busan-chatbot-backend',
            'error': str(e)
        }), 500


# === 에러 핸들링 ===
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': '요청한 리소스를 찾을 수 없습니다.',
        'status': 404
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': '서버 내부 오류가 발생했습니다.',
        'status': 500
    }), 500


@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        'error': '잘못된 요청입니다.',
        'status': 400
    }), 400


# === 메인 실행 ===
if __name__ == "__main__":
    print("🚀 부산 챗봇 시작 (리팩토링 완료)...")

    try:
        initialize_database(app)

        spaces_count = len(chat_handler.spaces_data) if chat_handler.spaces_data else 0
        print(f"📊 spaces_busan_youth.json: {spaces_count}개 공간 데이터 로드됨")

        print("✅ 모든 핸들러 준비 완료!")
        print("🔧 주요 기능:")
        print("   - 조건별 청년공간 검색 (지역/인원/목적)")
        print("   - 랜덤 청년공간 추천")
        print("   - 전체 청년공간 상세 보기")
        print("   - 키워드별 청년공간 검색")
        print("   - 청년 프로그램 검색")

        app.run(host='0.0.0.0', port=5001, debug=True)

    except Exception as e:
        print(f"❌ 서버 시작 실패: {e}")
else:
    initialize_database(app)
