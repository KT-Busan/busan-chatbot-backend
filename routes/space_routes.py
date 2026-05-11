import json
import os
from flask import Blueprint, request, jsonify
from handlers.space_handler import space_handler
from handlers.base_handler import BaseHandler

space_bp = Blueprint('space', __name__, url_prefix='/api/spaces')

_base = BaseHandler()


def _error(msg, code=500):
    return jsonify({'success': False, 'error': msg}), code


@space_bp.route('', methods=['GET'])
def get_spaces():
    return jsonify(space_handler.get_all_spaces())


@space_bp.route('/all', methods=['GET'])
def get_all_spaces_formatted():
    return jsonify(space_handler.get_all_spaces_formatted())


@space_bp.route('/region/<region>', methods=['GET'])
def get_spaces_by_region(region):
    return jsonify(space_handler.get_spaces_by_region(region))


@space_bp.route('/search', methods=['GET'])
def search_spaces():
    keyword = request.args.get('keyword', '')
    return jsonify(space_handler.search_spaces_by_keyword(keyword))


@space_bp.route('/detail/<space_name>', methods=['GET'])
def get_space_detail(space_name):
    return jsonify(space_handler.get_space_detail(space_name))


@space_bp.route('/crawl', methods=['POST'])
def crawl_spaces():
    return jsonify(space_handler.crawl_spaces_manually())


@space_bp.route('/cache-data', methods=['GET'])
def get_cache_data():
    try:
        merged_data = space_handler.get_merged_spaces_data()
        return jsonify({
            'success': True,
            'data': merged_data,
            'count': len(merged_data),
            'message': f"{len(merged_data)}개의 센터 데이터를 불러왔습니다."
        })
    except Exception as e:
        return _error("센터 데이터를 불러오는 중 오류가 발생했습니다.")


@space_bp.route('/keyword-data', methods=['GET'])
def get_keyword_data():
    try:
        config_path = _base.get_config_path()
        keyword_file = os.path.join(config_path, 'spaces_busan_keyword.json')

        if not os.path.exists(keyword_file):
            return _error("키워드 데이터 파일을 찾을 수 없습니다.", 404)

        with open(keyword_file, 'r', encoding='utf-8') as f:
            keyword_data = json.load(f).get('spaces_busan_keyword', [])

        return jsonify({
            'success': True,
            'data': keyword_data,
            'count': len(keyword_data),
            'message': f"{len(keyword_data)}개의 키워드 데이터를 불러왔습니다."
        })
    except Exception as e:
        return _error("키워드 데이터를 불러오는 중 오류가 발생했습니다.")


@space_bp.route('/busan-youth', methods=['GET'])
def get_busan_youth_spaces():
    try:
        config_path = _base.get_config_path()
        spaces_file = os.path.join(config_path, 'spaces_busan_youth.json')

        if not os.path.exists(spaces_file):
            return _error("spaces_busan_youth.json 파일을 찾을 수 없습니다.", 404)

        with open(spaces_file, 'r', encoding='utf-8') as f:
            spaces_data = json.load(f).get('spaces_busan_youth', [])

        if not spaces_data:
            return _error("청년공간 데이터가 없습니다.", 404)

        return jsonify({
            'success': True,
            'data': spaces_data,
            'count': len(spaces_data),
            'message': f"{len(spaces_data)}개의 청년공간 데이터를 반환했습니다."
        })
    except Exception as e:
        return _error("청년공간 데이터를 가져오는 중 오류가 발생했습니다.")


@space_bp.route('/rental-spaces/<center_name>', methods=['GET'])
def get_rental_spaces(center_name):
    try:
        config_path = _base.get_config_path()
        spaces_file = os.path.join(config_path, 'spaces_busan_youth.json')

        if not os.path.exists(spaces_file):
            return _error("대여공간 데이터 파일을 찾을 수 없습니다.", 404)

        with open(spaces_file, 'r', encoding='utf-8') as f:
            all_spaces = json.load(f).get('spaces_busan_youth', [])

        center_spaces = [s for s in all_spaces if s.get('parent_facility') == center_name]

        return jsonify({
            'success': True,
            'data': center_spaces,
            'count': len(center_spaces),
            'center_name': center_name,
            'message': f"{center_name}의 {len(center_spaces)}개 대여공간을 찾았습니다."
        })
    except Exception as e:
        return _error("대여공간 데이터를 불러오는 중 오류가 발생했습니다.")


@space_bp.route('/overrides/status', methods=['GET'])
def get_overrides_status():
    try:
        from services.youth_space_crawler import get_cache_data_only
        override_spaces = space_handler.load_overrides_data()
        cache_spaces = get_cache_data_only()
        merged_count = len(space_handler.get_merged_spaces_data())
        return jsonify({
            'success': True,
            'stats': {
                'cache_count': len(cache_spaces),
                'override_count': len(override_spaces),
                'override_names': [s.get('name', '') for s in override_spaces],
                'total_merged': merged_count
            },
            'message': f'Override: {len(override_spaces)}개, 캐시: {len(cache_spaces)}개, 병합: {merged_count}개'
        })
    except Exception as e:
        return _error("Override 상태를 확인할 수 없습니다.")


@space_bp.route('/overrides/reload', methods=['POST'])
def reload_overrides():
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
        return _error("Override 데이터 재로드에 실패했습니다.")


@space_bp.route('/overrides/test/<region>', methods=['GET'])
def test_region_overrides(region):
    try:
        from services.youth_space_crawler import get_cache_data_only
        cache_spaces = get_cache_data_only()
        cache_region = [s for s in cache_spaces if s.get('region') == region]
        merged_region = [s for s in space_handler.get_merged_spaces_data() if s.get('region') == region]

        changes = []
        for merged in merged_region:
            name = merged.get('name', '')
            cached = next((s for s in cache_region if s.get('name') == name), None)
            if cached:
                changed = [
                    {'field': f, 'old': cached.get(f, ''), 'new': merged.get(f, '')}
                    for f in ['contact', 'hours', 'address', 'homepage', 'sns']
                    if cached.get(f) != merged.get(f)
                ]
                if changed:
                    changes.append({'name': name, 'changes': changed})
            else:
                changes.append({'name': name, 'status': 'new_space'})

        return jsonify({
            'success': True,
            'region': region,
            'cache_spaces': len(cache_region),
            'merged_spaces': len(merged_region),
            'changes': changes,
            'message': f'{region} 지역에서 {len(changes)}개 공간에 변경사항이 있습니다.'
        })
    except Exception as e:
        return _error(f"{region} 지역의 Override 테스트에 실패했습니다.")


@space_bp.route('/overrides/compare/<space_name>', methods=['GET'])
def compare_space(space_name):
    try:
        from services.youth_space_crawler import get_cache_data_only
        cache_spaces = get_cache_data_only()
        cache_space = next((s for s in cache_spaces if space_name.lower() in s.get('name', '').lower()), None)
        override_spaces = space_handler.load_overrides_data()
        override_space = next((s for s in override_spaces if space_name.lower() in s.get('name', '').lower()), None)
        merged_spaces = space_handler.get_merged_spaces_data()
        merged_space = next((s for s in merged_spaces if space_name.lower() in s.get('name', '').lower()), None)

        return jsonify({
            'success': True,
            'comparison': {
                'space_name': space_name,
                'found_in_cache': cache_space is not None,
                'found_in_override': override_space is not None,
                'found_in_merged': merged_space is not None,
                'cache_data': cache_space,
                'override_data': override_space,
                'merged_data': merged_space,
                'using_override': override_space is not None
            },
            'message': f'{space_name} 데이터 비교 완료'
        })
    except Exception as e:
        return _error(f"{space_name} 데이터 비교에 실패했습니다.")


@space_bp.route('/region/<region>/debug', methods=['GET'])
def get_spaces_by_region_debug(region):
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
        return _error(f"{region} 지역 디버그 검색에 실패했습니다.")
