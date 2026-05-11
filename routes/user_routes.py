from flask import Blueprint, request, jsonify
from handlers.user_handler import user_handler

user_bp = Blueprint('user', __name__, url_prefix='/api')


@user_bp.route('/history/<anonymous_id>', methods=['GET'])
def get_history(anonymous_id):
    return jsonify(user_handler.get_user_history(anonymous_id))


@user_bp.route('/user/<anonymous_id>', methods=['GET'])
def get_user(anonymous_id):
    return jsonify(user_handler.get_user_info(anonymous_id))


@user_bp.route('/user', methods=['POST'])
def create_user():
    data = request.get_json() or {}
    return jsonify(user_handler.create_user(data.get('anonymous_id')))


@user_bp.route('/users/stats', methods=['GET'])
def get_users_stats():
    return jsonify(user_handler.get_users_stats())
