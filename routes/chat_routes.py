from flask import Blueprint, request, jsonify
from handlers.chat_handler import chat_handler

chat_bp = Blueprint('chat', __name__, url_prefix='/api')


@chat_bp.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '요청 데이터가 없습니다.'}), 400

    missing = [f for f in ['message', 'anonymousId', 'chatId'] if not data.get(f)]
    if missing:
        return jsonify({'success': False, 'error': f"필수 정보 누락: {', '.join(missing)}"}), 400

    result, status_code = chat_handler.process_chat_message(
        data['message'], data['anonymousId'], data['chatId']
    )
    return jsonify(result), status_code


@chat_bp.route('/chat/<chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    result, status_code = chat_handler.delete_chat_session(chat_id)
    return jsonify(result), status_code
