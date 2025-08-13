import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from datetime import datetime

from database.models import db, initialize_database
from handlers.chat_handler import chat_handler
from handlers.user_handler import user_handler
from handlers.program_handler import program_handler
from handlers.space_handler import space_handler

# --- 기본 설정 ---
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(os.environ.get('RENDER_DISK_PATH', basedir), 'instance')
os.makedirs(instance_path, exist_ok=True)

app = Flask(__name__)

# --- 데이터베이스 설정 ---
app.config.update({
    'SQLALCHEMY_DATABASE_URI': f'sqlite:///{os.path.join(instance_path, "chatbot.db")}',
    'SQLALCHEMY_TRACK_MODIFICATIONS': False
})
db.init_app(app)

# --- CORS 헤더 설정 ---
ALLOWED_ORIGINS = [
    'http://localhost:5173', 'http://localhost:3000',
    'http://127.0.0.1:5173', 'http://127.0.0.1:3000',
    'https://kt-busan.github.io'
]


@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
        response.headers.add('Access-Control-Allow-Origin', origin)

    response.headers.update({
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,PUT,POST,DELETE,OPTIONS'
    })
    return response


# --- 공통 에러 처리 함수 ---
def handle_api_error(error_message, status_code=500):
    """API 에러 처리를 위한 공통 함수"""
    return jsonify({"error": error_message}), status_code


def validate_required_fields(data, required_fields):
    """필수 필드 검증 함수"""
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        error_msg = f"필수 정보가 누락되었습니다: {', '.join(missing_fields)}"
        return error_msg, 400
    return None, None


def load_keyword_data(self):
    """spaces_busan_keyword.json 데이터 로드 및 정규화"""
    try:
        basedir = os.path.abspath(os.path.dirname(__file__))
        project_root = os.path.dirname(basedir)
        config_path = os.path.join(project_root, 'config')
        keyword_file = os.path.join(config_path, 'spaces_busan_keyword.json')

        if os.path.exists(keyword_file):
            with open(keyword_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                raw_data = data.get('spaces_busan_keyword', [])

                normalized_data = []
                for item in raw_data:
                    normalized_item = item.copy()
                    keywords = item.get('keywords')

                    if keywords is None:
                        normalized_item['keywords'] = []
                    elif isinstance(keywords, str):
                        normalized_item['keywords'] = [keywords]
                    elif isinstance(keywords, list):
                        normalized_item['keywords'] = keywords
                    else:
                        normalized_item['keywords'] = []

                    normalized_data.append(normalized_item)

                return normalized_data
        return []
    except Exception as e:
        print(f"키워드 데이터 로드 중 오류: {e}")
        return []


# === 채팅 관련 API ===
@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    """채팅 요청 처리 - Override 적용된 청년공간 데이터 사용"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    try:
        data = request.get_json()
        if not data:
            return handle_api_error("요청 데이터가 없습니다.", 400)

        required_fields = ["message", "anonymousId", "chatId"]
        error_msg, status_code = validate_required_fields(data, required_fields)
        if error_msg:
            return handle_api_error(error_msg, status_code)

        result, status_code = chat_handler.process_chat_message(
            data["message"], data["anonymousId"], data["chatId"]
        )
        return jsonify(result), status_code

    except Exception as e:
        return handle_api_error("서버 오류가 발생했습니다.")


@app.route("/api/chat/<chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    """채팅 삭제"""
    try:
        result, status_code = chat_handler.delete_chat_session(chat_id)
        return jsonify(result), status_code
    except Exception as e:
        return handle_api_error("서버 오류가 발생했습니다.")


# === 사용자 관련 API ===
@app.route("/api/history/<anonymous_id>", methods=["GET"])
def get_history(anonymous_id):
    """사용자 채팅 히스토리 조회"""
    try:
        history = user_handler.get_user_history(anonymous_id)
        return jsonify(history)
    except Exception as e:
        return handle_api_error("히스토리를 불러올 수 없습니다.")


@app.route("/api/user/<anonymous_id>", methods=["GET"])
def get_user(anonymous_id):
    """사용자 정보 조회"""
    try:
        result = user_handler.get_user_info(anonymous_id)
        return jsonify(result)
    except Exception as e:
        return handle_api_error("사용자 정보를 불러올 수 없습니다.")


@app.route("/api/user", methods=["POST"])
def create_user():
    """사용자 생성"""
    try:
        data = request.get_json()
        result = user_handler.create_user(data.get('anonymous_id'))
        return jsonify(result)
    except Exception as e:
        return handle_api_error("사용자 생성에 실패했습니다.")


@app.route("/api/users/stats", methods=["GET"])
def get_users_stats():
    """사용자 통계"""
    try:
        result = user_handler.get_users_stats()
        return jsonify(result)
    except Exception as e:
        return handle_api_error("통계 정보를 불러올 수 없습니다.")


# === 프로그램 관련 API ===
@app.route('/api/programs', methods=['GET'])
def get_programs():
    """전체 프로그램 목록"""
    try:
        result = program_handler.get_all_programs()
        return jsonify(result)
    except Exception as e:
        return handle_api_error("프로그램 목록을 불러올 수 없습니다.")


@app.route('/api/programs/region/<region>', methods=['GET'])
def get_programs_by_region_api(region):
    """지역별 프로그램 검색"""
    try:
        result = program_handler.get_programs_by_region(region)
        return jsonify(result)
    except Exception as e:
        return handle_api_error(f"{region} 지역 프로그램을 불러올 수 없습니다.")


@app.route('/api/programs/crawl', methods=['POST'])
def crawl_programs_now():
    """수동 프로그램 크롤링"""
    try:
        result = program_handler.crawl_programs_manually()
        return jsonify(result)
    except Exception as e:
        return handle_api_error("프로그램 크롤링에 실패했습니다.")


@app.route('/api/programs/search', methods=['GET'])
def search_programs():
    """키워드별 프로그램 검색"""
    try:
        keyword = request.args.get('keyword', '')
        result = program_handler.search_programs_by_keyword(keyword)
        return jsonify(result)
    except Exception as e:
        return handle_api_error("프로그램 검색에 실패했습니다.")


# === 청년공간 관련 API ===
@app.route('/api/spaces', methods=['GET'])
def get_spaces():
    """전체 청년공간 목록 (Override 적용)"""
    try:
        result = space_handler.get_all_spaces()
        return jsonify(result)
    except Exception as e:
        return handle_api_error("청년공간 목록을 불러올 수 없습니다.")


@app.route('/api/spaces/region/<region>', methods=['GET'])
def get_spaces_by_region_api(region):
    """지역별 청년공간 검색 (Override 적용)"""
    try:
        result = space_handler.get_spaces_by_region(region)
        return jsonify(result)
    except Exception as e:
        return handle_api_error(f"{region} 지역 청년공간을 불러올 수 없습니다.")


@app.route('/api/spaces/search', methods=['GET'])
def search_spaces_api():
    """키워드별 청년공간 검색 (Override 적용)"""
    try:
        keyword = request.args.get('keyword', '')
        result = space_handler.search_spaces_by_keyword(keyword)
        return jsonify(result)
    except Exception as e:
        return handle_api_error("청년공간 검색에 실패했습니다.")


@app.route('/api/spaces/all', methods=['GET'])
def get_all_spaces_formatted():
    """전체 청년공간 목록 (포맷된, Override 적용)"""
    try:
        result = space_handler.get_all_spaces_formatted()
        return jsonify(result)
    except Exception as e:
        return handle_api_error("청년공간 목록을 불러올 수 없습니다.")


@app.route('/api/spaces/crawl', methods=['POST'])
def crawl_spaces_now():
    """수동 청년공간 크롤링"""
    try:
        result = space_handler.crawl_spaces_manually()
        return jsonify(result)
    except Exception as e:
        return handle_api_error("청년공간 크롤링에 실패했습니다.")


@app.route('/api/spaces/detail/<space_name>', methods=['GET'])
def get_space_detail_api(space_name):
    """특정 공간의 상세 정보 (Override 적용)"""
    try:
        result = space_handler.get_space_detail(space_name)
        return jsonify(result)
    except Exception as e:
        return handle_api_error(f"{space_name} 공간 정보를 불러올 수 없습니다.")


# === Override 관련 API ===
@app.route('/api/spaces/overrides/status', methods=['GET'])
def get_overrides_status():
    """Override 데이터 상태 확인"""
    try:
        override_spaces = space_handler.load_overrides_data()

        from services.youth_space_crawler import get_cache_data_only
        cache_spaces = get_cache_data_only()

        override_names = [space.get('name', '') for space in override_spaces]
        merged_count = len(space_handler.get_merged_spaces_data())

        stats = {
            'cache_count': len(cache_spaces),
            'override_count': len(override_spaces),
            'override_names': override_names,
            'total_merged': merged_count
        }

        return jsonify({
            'success': True,
            'stats': stats,
            'message': f'Override: {len(override_spaces)}개, 캐시: {len(cache_spaces)}개, 병합: {merged_count}개'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Override 상태를 확인할 수 없습니다.'
        }), 500


@app.route('/api/spaces/overrides/test/<region>', methods=['GET'])
def test_region_with_overrides(region):
    """특정 지역의 Override 적용 테스트"""
    try:
        from services.youth_space_crawler import get_cache_data_only
        cache_spaces = get_cache_data_only()
        cache_region_spaces = [s for s in cache_spaces if s.get('region') == region]

        merged_spaces = space_handler.get_merged_spaces_data()
        merged_region_spaces = [s for s in merged_spaces if s.get('region') == region]

        changes = []
        for merged_space in merged_region_spaces:
            space_name = merged_space.get('name', '')
            cache_space = next((s for s in cache_region_spaces if s.get('name') == space_name), None)

            if cache_space:
                changed_fields = []
                for field in ['contact', 'hours', 'address', 'homepage', 'sns']:
                    if cache_space.get(field) != merged_space.get(field):
                        changed_fields.append({
                            'field': field,
                            'old': cache_space.get(field, ''),
                            'new': merged_space.get(field, '')
                        })

                if changed_fields:
                    changes.append({
                        'name': space_name,
                        'changes': changed_fields
                    })
            else:
                changes.append({
                    'name': space_name,
                    'status': 'new_space'
                })

        return jsonify({
            'success': True,
            'region': region,
            'cache_spaces': len(cache_region_spaces),
            'merged_spaces': len(merged_region_spaces),
            'changes': changes,
            'message': f'{region} 지역에서 {len(changes)}개 공간에 변경사항이 있습니다.'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'{region} 지역의 Override 테스트에 실패했습니다.'
        }), 500


@app.route('/api/spaces/overrides/reload', methods=['POST'])
def reload_overrides_data():
    """Override 데이터 강제 재로드"""
    try:
        override_spaces = space_handler.load_overrides_data()
        merged_spaces = space_handler.get_merged_spaces_data()

        return jsonify({
            'success': True,
            'override_count': len(override_spaces),
            'merged_count': len(merged_spaces),
            'message': f'Override 데이터 재로드 완료: {len(override_spaces)}개 Override 적용'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Override 데이터 재로드에 실패했습니다.'
        }), 500


@app.route('/api/spaces/overrides/compare/<space_name>', methods=['GET'])
def compare_space_data(space_name):
    """특정 공간의 캐시 vs Override 데이터 비교"""
    try:
        from services.youth_space_crawler import get_cache_data_only
        cache_spaces = get_cache_data_only()
        cache_space = next((s for s in cache_spaces if space_name.lower() in s.get('name', '').lower()), None)

        override_spaces = space_handler.load_overrides_data()
        override_space = next((s for s in override_spaces if space_name.lower() in s.get('name', '').lower()), None)

        merged_spaces = space_handler.get_merged_spaces_data()
        merged_space = next((s for s in merged_spaces if space_name.lower() in s.get('name', '').lower()), None)

        comparison = {
            'space_name': space_name,
            'found_in_cache': cache_space is not None,
            'found_in_override': override_space is not None,
            'found_in_merged': merged_space is not None,
            'cache_data': cache_space,
            'override_data': override_space,
            'merged_data': merged_space,
            'using_override': override_space is not None
        }

        return jsonify({
            'success': True,
            'comparison': comparison,
            'message': f'{space_name} 데이터 비교 완료'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'{space_name} 데이터 비교에 실패했습니다.'
        }), 500


@app.route('/api/spaces/region/<region>/debug', methods=['GET'])
def get_spaces_by_region_debug(region):
    """지역별 청년공간 검색 (디버그 정보 포함)"""
    try:
        result = space_handler.get_spaces_by_region(region)

        override_spaces = space_handler.load_overrides_data()
        region_overrides = [s for s in override_spaces if s.get('region') == region]

        if result.get('success'):
            result['debug'] = {
                'override_count_in_region': len(region_overrides),
                'override_names': [s.get('name', '') for s in region_overrides],
                'data_source': 'merged (cache + override)'
            }

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'{region} 지역 디버그 검색에 실패했습니다.'
        }), 500


@app.route('/api/spaces/busan-youth', methods=['GET'])
def get_busan_youth_spaces():
    """부산 청년공간 데이터 반환 (JSON 파일 형식으로)"""
    try:
        basedir = os.path.abspath(os.path.dirname(__file__))
        config_path = os.path.join(basedir, 'config')
        spaces_file = os.path.join(config_path, 'spaces_busan_youth.json')

        print(f"🔍 JSON 파일 경로: {spaces_file}")
        print(f"🔍 파일 존재 여부: {os.path.exists(spaces_file)}")

        if not os.path.exists(spaces_file):
            return jsonify({
                'success': False,
                'data': [],
                'count': 0,
                'message': 'spaces_busan_youth.json 파일을 찾을 수 없습니다.'
            }), 404

        with open(spaces_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            spaces_data = json_data.get('spaces_busan_youth', [])

        if not spaces_data:
            return jsonify({
                'success': False,
                'data': [],
                'count': 0,
                'message': '청년공간 데이터가 없습니다.'
            }), 404

        return jsonify({
            'success': True,
            'data': spaces_data,
            'count': len(spaces_data),
            'message': f'{len(spaces_data)}개의 청년공간 데이터를 반환했습니다.'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'data': [],
            'count': 0,
            'message': '청년공간 데이터를 가져오는 중 오류가 발생했습니다.'
        }), 500


# === 디버깅 관련 API ===
def get_file_path_status():
    """파일 경로 상태 확인 공통 함수"""
    possible_paths = [
        os.path.join(instance_path, 'youth_spaces_cache.json'),
        os.path.join(instance_path, 'youth_spaces_overrides.json'),
        os.path.join(basedir, 'config', 'spaces_busan_youth.json'),
    ]

    path_status = {}
    for path in possible_paths:
        path_status[path] = {
            'exists': os.path.exists(path),
            'readable': os.path.exists(path) and os.access(path, os.R_OK) if os.path.exists(path) else False
        }
    return path_status


@app.route('/api/debug/spaces-status', methods=['GET'])
def get_spaces_debug_status():
    """청년공간 데이터 로딩 상태 디버깅"""
    try:
        cache_spaces = space_handler.load_overrides_data()
        merged_spaces = space_handler.get_merged_spaces_data()
        chat_spaces_count = len(chat_handler.spaces_data) if hasattr(chat_handler,
                                                                     'spaces_data') and chat_handler.spaces_data else 0

        return jsonify({
            'success': True,
            'data_status': {
                'override_spaces': len(cache_spaces),
                'merged_spaces': len(merged_spaces),
                'chat_handler_spaces': chat_spaces_count
            },
            'file_paths': get_file_path_status(),
            'current_dir': os.getcwd(),
            'app_dir': basedir,
            'instance_path': instance_path,
            'render_path': os.environ.get('RENDER_DISK_PATH', 'None'),
            'sample_merged_space': merged_spaces[0] if merged_spaces else None
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/debug/reload-spaces', methods=['POST'])
def reload_spaces_data():
    """청년공간 데이터 강제 재로드"""
    try:
        old_override_count = len(space_handler.load_overrides_data())
        old_merged_count = len(space_handler.get_merged_spaces_data())

        override_spaces = space_handler.load_overrides_data()
        merged_spaces = space_handler.get_merged_spaces_data()

        if hasattr(chat_handler, 'load_spaces_data'):
            chat_handler.spaces_data = chat_handler.load_spaces_data()

        return jsonify({
            'success': True,
            'message': '데이터 재로드 완료',
            'override_count': len(override_spaces),
            'merged_count': len(merged_spaces),
            'changes': {
                'override': f'{old_override_count} → {len(override_spaces)}',
                'merged': f'{old_merged_count} → {len(merged_spaces)}'
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/spaces/cache-data', methods=['GET'])
def get_cache_data():
    """센터 데이터 반환 (youth_spaces_cache.json) - 없으면 자동 생성"""
    try:
        basedir = os.path.abspath(os.path.dirname(__file__))
        instance_path = os.path.join(basedir, 'instance')
        config_path = os.path.join(basedir, 'config')
        cache_file = os.path.join(instance_path, 'youth_spaces_cache.json')
        spaces_file = os.path.join(config_path, 'spaces_busan_youth.json')

        if not os.path.exists(cache_file):
            if os.path.exists(spaces_file):
                with open(spaces_file, 'r', encoding='utf-8') as f:
                    spaces_data = json.load(f)
                    if isinstance(spaces_data, dict):
                        spaces_data = spaces_data.get('spaces_busan_youth', spaces_data)
                os.makedirs(instance_path, exist_ok=True)
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump({"data": spaces_data}, f, ensure_ascii=False, indent=2)
                print(f"✅ {cache_file} 자동 생성 완료 ({len(spaces_data)}개 데이터)")
            else:
                return {
                    'success': False,
                    'data': [],
                    'count': 0,
                    'message': '센터 데이터 파일을 찾을 수 없습니다.'
                }, 404

        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return {
            'success': True,
            'data': data.get('data', []),
            'count': len(data.get('data', [])),
            'message': f"{len(data.get('data', []))}개의 센터 데이터를 불러왔습니다."
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': [],
            'count': 0,
            'message': '센터 데이터를 불러오는 중 오류가 발생했습니다.'
        }, 500


@app.route('/api/spaces/keyword-data', methods=['GET'])
def get_keyword_data():
    """키워드 데이터 반환 (spaces_busan_keyword.json)"""
    try:
        basedir = os.path.abspath(os.path.dirname(__file__))
        config_path = os.path.join(basedir, 'config')
        keyword_file = os.path.join(config_path, 'spaces_busan_keyword.json')

        if os.path.exists(keyword_file):
            with open(keyword_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                keyword_data = data.get('spaces_busan_keyword', [])
                return {
                    'success': True,
                    'data': keyword_data,
                    'count': len(keyword_data),
                    'message': f"{len(keyword_data)}개의 키워드 데이터를 불러왔습니다."
                }
        else:
            return {
                'success': False,
                'data': [],
                'count': 0,
                'message': '키워드 데이터 파일을 찾을 수 없습니다.'
            }, 404

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': [],
            'count': 0,
            'message': '키워드 데이터를 불러오는 중 오류가 발생했습니다.'
        }, 500


@app.route('/api/spaces/rental-spaces/<center_name>', methods=['GET'])
def get_rental_spaces(center_name):
    """특정 센터의 대여가능한 공간들 반환"""
    try:
        basedir = os.path.abspath(os.path.dirname(__file__))
        config_path = os.path.join(basedir, 'config')
        spaces_file = os.path.join(config_path, 'spaces_busan_youth.json')

        if os.path.exists(spaces_file):
            with open(spaces_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_spaces = data.get('spaces_busan_youth', [])

                # 해당 센터의 공간들만 필터링
                center_spaces = [
                    space for space in all_spaces
                    if space.get('parent_facility') == center_name
                ]

                return {
                    'success': True,
                    'data': center_spaces,
                    'count': len(center_spaces),
                    'center_name': center_name,
                    'message': f"{center_name}의 {len(center_spaces)}개 대여공간을 찾았습니다."
                }
        else:
            return {
                'success': False,
                'data': [],
                'count': 0,
                'message': '대여공간 데이터 파일을 찾을 수 없습니다.'
            }, 404

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': [],
            'count': 0,
            'message': '대여공간 데이터를 불러오는 중 오류가 발생했습니다.'
        }, 500


# === 헬스체크 ===
@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health_check():
    """시스템 헬스체크 (Override 상태 포함)"""
    try:
        override_count = len(space_handler.load_overrides_data())
        merged_count = len(space_handler.get_merged_spaces_data())
        chat_spaces_count = len(chat_handler.spaces_data) if hasattr(chat_handler,
                                                                     'spaces_data') and chat_handler.spaces_data else 0

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
        return jsonify({
            'status': 'unhealthy',
            'service': 'busan-chatbot-backend',
            'error': str(e)
        }), 500


# === 에러 핸들링 ===
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '요청한 리소스를 찾을 수 없습니다.', 'status': 404}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '서버 내부 오류가 발생했습니다.', 'status': 500}), 500


@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': '잘못된 요청입니다.', 'status': 400}), 400


# === 메인 실행 ===
def init_app():
    """앱 초기화"""
    try:
        initialize_database(app)
        return True
    except Exception as e:
        return False


if __name__ == "__main__":
    if init_app():
        app.run(host='0.0.0.0', port=5001, debug=True)
else:
    initialize_database(app)
