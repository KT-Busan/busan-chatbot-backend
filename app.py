import os
import time
from flask import Flask, request, jsonify, make_response
from dotenv import load_dotenv
from datetime import datetime

from database.models import db, initialize_database
from handlers.chat_handler import chat_handler
from handlers.space_handler import space_handler
from handlers.base_handler import BaseHandler

from routes.chat_routes import chat_bp
from routes.user_routes import user_bp
from routes.space_routes import space_bp
from routes.program_routes import program_bp

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(os.environ.get('RENDER_DISK_PATH', basedir), 'instance')
os.makedirs(instance_path, exist_ok=True)

app = Flask(__name__)

app.config.update({
    'SQLALCHEMY_DATABASE_URI': f'sqlite:///{os.path.join(instance_path, "chatbot.db")}',
    'SQLALCHEMY_TRACK_MODIFICATIONS': False
})
db.init_app(app)

_default_origins = (
    'http://localhost:5173,http://localhost:3000,'
    'http://127.0.0.1:5173,http://127.0.0.1:3000,'
    'https://kt-busan.github.io,https://busan-chatbot-backend.onrender.com'
)
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get('ALLOWED_ORIGINS', _default_origins).split(',') if o.strip()]

_CORS_HEADERS = {
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,PUT,POST,DELETE,OPTIONS',
    'Access-Control-Allow-Credentials': 'true',
}


def _is_allowed_origin(origin):
    if not origin:
        return False
    if origin in ALLOWED_ORIGINS:
        return True
    # 로컬 개발: localhost / 127.0.0.1 은 포트 무관 허용
    if origin.startswith('http://localhost:') or origin.startswith('http://127.0.0.1:'):
        return True
    return False


@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        origin = request.headers.get('Origin')
        if _is_allowed_origin(origin):
            res = make_response('', 204)
            res.headers['Access-Control-Allow-Origin'] = origin
            res.headers.update(_CORS_HEADERS)
            return res


@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if _is_allowed_origin(origin):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers.update(_CORS_HEADERS)
    return response


app.register_blueprint(chat_bp)
app.register_blueprint(user_bp)
app.register_blueprint(space_bp)
app.register_blueprint(program_bp)


@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        override_count = len(space_handler.load_overrides_data())
        merged_count = len(space_handler.get_merged_spaces_data())
        chat_spaces_count = len(chat_handler.spaces_data) if hasattr(chat_handler, 'spaces_data') and chat_handler.spaces_data else 0

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
                'override_system': 'active'
            },
            'data_status': {
                'override_spaces': f'{override_count} spaces',
                'merged_spaces': f'{merged_count} spaces',
                'chat_handler_spaces': f'{chat_spaces_count} spaces'
            }
        })
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'service': 'busan-chatbot-backend', 'error': str(e)}), 500


@app.route('/api/debug/spaces-status', methods=['GET'])
def get_spaces_debug_status():
    try:
        _base = BaseHandler()
        merged_spaces = space_handler.get_merged_spaces_data()
        chat_spaces_count = len(chat_handler.spaces_data) if hasattr(chat_handler, 'spaces_data') and chat_handler.spaces_data else 0

        return jsonify({
            'success': True,
            'data_status': {
                'override_spaces': len(space_handler.load_overrides_data()),
                'merged_spaces': len(merged_spaces),
                'chat_handler_spaces': chat_spaces_count
            },
            'current_dir': os.getcwd(),
            'app_dir': basedir,
            'instance_path': instance_path,
            'config_path': _base.get_config_path(),
            'render_path': os.environ.get('RENDER_DISK_PATH', 'None'),
            'sample_merged_space': merged_spaces[0] if merged_spaces else None
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/debug/reload-spaces', methods=['POST'])
def reload_spaces_data():
    try:
        old_merged = len(space_handler.get_merged_spaces_data())
        if hasattr(chat_handler, 'load_spaces_data'):
            chat_handler.spaces_data = chat_handler.load_spaces_data()
        new_merged = len(space_handler.get_merged_spaces_data())

        return jsonify({
            'success': True,
            'message': '데이터 재로드 완료',
            'merged_count': new_merged,
            'changes': {'merged': f'{old_merged} → {new_merged}'}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# 사용자 요청과 분리된 크롤링 갱신용 관리자 토큰.
# TODO: 지금은 단순 토큰 비교만 하고 있음 - 정식 인증(예: 서명된 JWT, IP 제한)으로 교체할 것.
ADMIN_REFRESH_TOKEN = os.environ.get('ADMIN_REFRESH_TOKEN')


@app.route('/api/admin/refresh-crawl', methods=['POST'])
def admin_refresh_crawl():
    token = request.headers.get('X-Admin-Token', '')
    if not ADMIN_REFRESH_TOKEN or token != ADMIN_REFRESH_TOKEN:
        return jsonify({'success': False, 'error': '인증되지 않은 요청입니다.'}), 401

    from services.youth_space_crawler import crawl_new_data
    from services.youth_program_crawler import refresh_programs_cache

    start = time.time()
    try:
        spaces = crawl_new_data()
        programs = refresh_programs_cache()
        elapsed = round(time.time() - start, 2)

        return jsonify({
            'success': True,
            'message': f'크롤링 갱신 완료 ({elapsed}초 소요)',
            'elapsed_seconds': elapsed,
            'spaces_count': len(spaces),
            'programs_count': len(programs),
            'refreshed_at': datetime.utcnow().isoformat()
        })
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        return jsonify({'success': False, 'error': str(e), 'elapsed_seconds': elapsed}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': '요청한 리소스를 찾을 수 없습니다.', 'status': 404}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': '서버 내부 오류가 발생했습니다.', 'status': 500}), 500


@app.errorhandler(400)
def bad_request(error):
    return jsonify({'success': False, 'error': '잘못된 요청입니다.', 'status': 400}), 400


def warm_up_youth_data():
    """서버 부팅 시 1회 실행: 청년공간/프로그램 캐시가 없거나 오래됐으면 미리 크롤링해둔다.
    요청 처리 경로에서는 크롤링을 절대 실행하지 않고 이 캐시만 읽는다."""
    try:
        from services.youth_space_crawler import ensure_spaces_cache_fresh
        from services.youth_program_crawler import ensure_programs_cache_fresh
        ensure_spaces_cache_fresh()
        ensure_programs_cache_fresh()
    except Exception as e:
        print(f"⚠️ 부팅 시 데이터 준비 실패, 기존 캐시 파일로 계속 진행합니다: {e}")


def init_app():
    try:
        initialize_database(app)
        warm_up_youth_data()
        return True
    except Exception:
        return False


if __name__ == "__main__":
    if init_app():
        port = int(os.environ.get('PORT', 5001))
        app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_ENV') == 'development')
else:
    init_app()
