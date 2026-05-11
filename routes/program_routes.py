from flask import Blueprint, request, jsonify
from handlers.program_handler import program_handler

program_bp = Blueprint('program', __name__, url_prefix='/api/programs')


@program_bp.route('', methods=['GET'])
def get_programs():
    return jsonify(program_handler.get_all_programs())


@program_bp.route('/region/<region>', methods=['GET'])
def get_programs_by_region(region):
    return jsonify(program_handler.get_programs_by_region(region))


@program_bp.route('/search', methods=['GET'])
def search_programs():
    keyword = request.args.get('keyword', '')
    return jsonify(program_handler.search_programs_by_keyword(keyword))


@program_bp.route('/crawl', methods=['POST'])
def crawl_programs():
    return jsonify(program_handler.crawl_programs_manually())
