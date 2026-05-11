import os
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


@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        origin = request.headers.get('Origin')
        if origin in ALLOWED_ORIGINS:
            res = make_response('', 204)
            res.headers['Access-Control-Allow-Origin'] = origin
            res.headers.update(_CORS_HEADERS)
            return res


@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
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


@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': '요청한 리소스를 찾을 수 없습니다.', 'status': 404}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': '서버 내부 오류가 발생했습니다.', 'status': 500}), 500


@app.errorhandler(400)
def bad_request(error):
    return jsonify({'success': False, 'error': '잘못된 요청입니다.', 'status': 400}), 400


def init_app():
    try:
        initialize_database(app)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    if init_app():
        port = int(os.environ.get('PORT', 5001))
        app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_ENV') == 'development')
else:
    initialize_database(app)
