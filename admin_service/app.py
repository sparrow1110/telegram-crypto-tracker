from flask import Flask, jsonify, request
from flasgger import Swagger, swag_from
from .admin_panel import AdminPanel
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
swagger = Swagger(
    app,
    template={
        "swagger": "2.0",
        "info": {
            "title": "Admin Service API",
            "description": "API для администрирования криптобота",
            "version": "1.0.0",
        },
        "consumes": ["application/json"],
        "produces": ["application/json"],
    },
)
API_TOKEN = os.getenv('API_TOKEN', 'your-secret-api-token')
admin = AdminPanel(
    user_service_url=os.getenv('USER_SERVICE_URL', 'http://user_service:5001'),
    crypto_service_url=os.getenv('CRYPTO_SERVICE_URL', 'http://crypto_service:5003'),
    api_token=API_TOKEN,
)


def format_response(data=None, errors=None, meta=None, status_code=200):
    response = {'data': data} if data is not None else {}

    if errors:
        if not isinstance(errors, list):
            errors = [errors]
        response['errors'] = [e if isinstance(e, dict) else {'message': str(e)} for e in errors]

    if meta:
        response['meta'] = meta
    return jsonify(response), status_code


def verify_token():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    return token == API_TOKEN


def check_admin(requester_id):
    try:
        return admin.is_admin(requester_id)
    except Exception as e:
        return False


@app.route('/v1/admins/<int:user_id>/status', methods=['GET'])
@swag_from('docs/is_admin.yaml')
def is_admin(user_id):
    if not verify_token():
        return format_response(
            errors=[{'code': 'Unauthorized', 'message': 'Invalid or missing API token'}], status_code=401
        )
    try:
        is_admin = admin.is_admin(user_id)
        return format_response(data={'is_admin': is_admin})
    except Exception as e:
        return format_response(errors=[{'code': 'InternalServerError', 'message': str(e)}], status_code=500)


@app.route('/v1/stats', methods=['GET'])
@swag_from('docs/get_stats.yaml')
def get_stats():
    requester_id = request.json.get('requester_id')
    if not requester_id or not check_admin(requester_id):
        return format_response(errors=[{'code': 'Forbidden', 'message': 'User is not an admin'}], status_code=403)
    try:
        stats = admin.get_bot_stats(requester_id)
        return format_response(data={'stats': stats})
    except Exception as e:
        return format_response(errors=[{'code': 'InternalServerError', 'message': str(e)}], status_code=500)


@app.route('/v1/stats/popular-cryptos', methods=['GET'])
@swag_from('docs/popular_cryptos.yaml')
def popular_cryptos():
    requester_id = request.json.get('requester_id')
    if not requester_id or not check_admin(requester_id):
        return format_response(errors=[{'code': 'Forbidden', 'message': 'User is not an admin'}], status_code=403)
    try:
        popular = admin.get_popular_cryptos(requester_id)
        return format_response(data={'popular': popular})
    except Exception as e:
        return format_response(errors=[{'code': 'InternalServerError', 'message': str(e)}], status_code=500)


@app.route('/v1/users/<int:user_id>/block', methods=['POST'])
@swag_from('docs/block_user.yaml')
def block_user(user_id):
    requester_id = request.json.get('requester_id')
    if not requester_id or not check_admin(requester_id):
        return format_response(errors=[{'code': 'Forbidden', 'message': 'User is not an admin'}], status_code=403)
    try:
        success = admin.block_user(user_id, requester_id)
        if success:
            return format_response(data={'user_id': user_id, 'is_blocked': True, 'action': 'admin_blocked'})
        return format_response(errors=[{'code': 'NotFound', 'message': 'User not found'}], status_code=404)
    except Exception as e:
        return format_response(errors=[{'code': 'InternalServerError', 'message': str(e)}], status_code=500)


@app.route('/v1/users/<int:user_id>/unblock', methods=['POST'])
@swag_from('docs/unblock_user.yaml')
def unblock_user(user_id):
    requester_id = request.json.get('requester_id')
    if not requester_id or not check_admin(requester_id):
        return format_response(errors=[{'code': 'Forbidden', 'message': 'User is not an admin'}], status_code=403)
    try:
        success = admin.unblock_user(user_id, requester_id)
        if success:
            return format_response(data={'user_id': user_id, 'is_blocked': False, 'action': 'admin_unblocked'})
        return format_response(errors=[{'code': 'NotFound', 'message': 'User not found'}], status_code=404)
    except Exception as e:
        return format_response(errors=[{'code': 'InternalServerError', 'message': str(e)}], status_code=500)


@app.errorhandler(404)
def not_found(error):
    return format_response(errors=[{'code': 'NotFound', 'message': 'Resource not found'}], status_code=404)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
