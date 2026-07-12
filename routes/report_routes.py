import os
from flask import Blueprint, request, jsonify
from database.models import db, ErrorReport

report_bp = Blueprint('report', __name__, url_prefix='/api/reports')

ALLOWED_CATEGORIES = {'홈페이지', '전화번호', '주소', '기타'}

# /api/admin/refresh-crawl과 동일한 관리자 토큰을 재사용한다.
# TODO: 지금은 단순 토큰 비교만 하고 있음 - 정식 인증(로그인/역할 기반 등)으로 교체할 것.
ADMIN_REPORT_TOKEN = os.environ.get('ADMIN_REFRESH_TOKEN')


@report_bp.route('', methods=['POST'])
def create_report():
    data = request.get_json(silent=True) or {}
    center_name = (data.get('center_name') or '').strip()
    category = (data.get('category') or '').strip()
    content = (data.get('content') or '').strip()
    anonymous_id = (data.get('anonymous_id') or '').strip() or None

    if not center_name or not content:
        return jsonify({'success': False, 'error': '센터명과 신고 내용을 입력해주세요.'}), 400

    if category not in ALLOWED_CATEGORIES:
        category = '기타'

    report = ErrorReport(
        center_name=center_name,
        category=category,
        content=content,
        anonymous_id=anonymous_id
    )
    db.session.add(report)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '신고가 접수되었습니다. 확인 후 반영하겠습니다.',
        'id': report.id
    }), 201


@report_bp.route('', methods=['GET'])
def list_reports():
    token = request.headers.get('X-Admin-Token', '')
    if not ADMIN_REPORT_TOKEN or token != ADMIN_REPORT_TOKEN:
        return jsonify({'success': False, 'error': '인증되지 않은 요청입니다.'}), 401

    reports = ErrorReport.query.order_by(ErrorReport.created_at.desc()).all()
    return jsonify({
        'success': True,
        'count': len(reports),
        'data': [
            {
                'id': r.id,
                'center_name': r.center_name,
                'category': r.category,
                'content': r.content,
                'anonymous_id': r.anonymous_id,
                'created_at': r.created_at.isoformat()
            }
            for r in reports
        ]
    })
