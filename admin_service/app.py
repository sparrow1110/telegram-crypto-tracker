from flask import Flask, jsonify, request
from .admin_panel import AdminPanel
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
admin = AdminPanel(
    user_service_url=f"http://localhost:{os.getenv('USER_SERVICE_PORT')}",
    crypto_service_url=f"http://localhost:{os.getenv('CRYPTO_SERVICE_PORT')}"
)


def format_response(data=None, errors=None, meta=None, status_code=200):
    response = {
        'data': data,
    }
    if errors:
        response['errors'] = errors
    if meta:
        response['meta'] = meta

    return jsonify(response), status_code

@app.route('/v1/admins/<int:user_id>/status', methods=['GET'])
def is_admin(user_id):
    try:
        is_admin = admin.is_admin(user_id)
        return format_response(data={'is_admin': is_admin})
    except Exception as e:
        return format_response(
            errors=[{'code': 'InternalServerError', 'message': str(e)}],
            status_code=500
        )


@app.route('/v1/stats', methods=['GET'])
def get_stats():
    try:
        stats = admin.get_bot_stats()
        return format_response(data={'stats': stats})
    except Exception as e:
        return format_response(
            errors=[{'code': 'InternalServerError', 'message': str(e)}],
            status_code=500
        )

@app.route('/v1/stats/popular-cryptos', methods=['GET'])
def popular_cryptos():
    try:
        popular = admin.get_popular_cryptos()
        return format_response(data={'popular': popular})
    except Exception as e:
        return format_response(
            errors=[{'code': 'InternalServerError', 'message': str(e)}],
            status_code=500
        )

@app.route('/v1/users/<int:user_id>/block', methods=['POST'])
def block_user(user_id):
    """Админская блокировка пользователя"""
    try:
        success = admin.block_user(user_id)
        if success:
            return format_response(
                data={
                    'user_id': user_id,
                    'is_blocked': True,
                    'action': 'admin_blocked'
                }
            )
        return format_response(
            errors=[{'code': 'NotFound', 'message': 'User not found'}],
            status_code=404
        )
    except Exception as e:
        return format_response(
            errors=[{'code': 'BlockFailed', 'message': str(e)}],
            status_code=400
        )

@app.route('/v1/users/<int:user_id>/unblock', methods=['POST'])
def unblock_user(user_id):
    """Админская разблокировка пользователя"""
    try:
        success = admin.unblock_user(user_id)
        if success:
            return format_response(
                data={
                    'user_id': user_id,
                    'is_blocked': False,
                    'action': 'admin_unblocked'
                }
            )
        return format_response(
            errors=[{'code': 'NotFound', 'message': 'User not found'}],
            status_code=404
        )
    except Exception as e:
        return format_response(
            errors=[{'code': 'UnblockFailed', 'message': str(e)}],
            status_code=400
        )

@app.errorhandler(404)
def not_found(error):
    return format_response(
        errors=[{'code': 'NotFound', 'message': 'Resource not found'}],
        status_code=404
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)