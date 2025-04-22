# user_service/app.py
from flask import Flask, jsonify, request
from user_service.models import db
from user_service.db_handler import DatabaseManager
import os
from dotenv import load_dotenv

load_dotenv()
db_manager = DatabaseManager()

def create_app(test_config=None):
    app = Flask(__name__)

    if test_config:
        # Тестовая конфигурация
        app.config.from_mapping(test_config)
    else:
        # Боевая/локальная конфигурация
        app.config['SQLALCHEMY_DATABASE_URI'] = (
            f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@"
            f"{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
        )
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    register_routes(app)

    return app

def format_response(data=None, errors=None, meta=None, status_code=200):
    response = {'data': data} if data is not None else {}

    if errors:
        # Обеспечиваем правильную структуру ошибок
        if not isinstance(errors, list):
            errors = [errors]
        response['errors'] = [e if isinstance(e, dict) else {'message': str(e)} for e in errors]

    if meta:
        response['meta'] = meta
    return jsonify(response), status_code

def register_routes(app):
    @app.route('/v1/stats', methods=['GET'])
    def get_stats():
        try:
            stats = {
                'user_count': db_manager.get_user_count(),
                'active_users_24h': db_manager.get_active_users(1),
                'active_users_7d': db_manager.get_active_users(7),
                'blocked_count': db_manager.get_blocked_users_count(),
                'favorites_count': db_manager.get_count_favorite(),
                'popular_commands': db_manager.get_popular_commands(),
            }
            return format_response(data=stats)
        except Exception as e:
            return format_response(
                errors=[{'code': 'InternalServerError', 'message': str(e)}],
                status_code=500
            )

    @app.route('/v1/users', methods=['POST'])
    def register_user():
        data = request.json
        try:
            success, is_new = db_manager.register_user(
                data['user_id'],
                data.get('username'),
                data.get('first_name'),
                data.get('last_name')
            )

            if success:
                return format_response(
                    data={
                        'user_id': data['user_id'],
                        'username': data.get('username'),
                        'is_new': is_new  # Добавляем информацию о типе операции
                    },
                    status_code=201 if is_new else 200
                )

            return format_response(
                errors=[{'code': 'RegistrationFailed', 'message': 'User registration failed'}],
                status_code=400
            )

        except Exception as e:
            return format_response(
                errors=[{'code': 'InternalServerError', 'message': str(e)}],
                status_code=500
            )

    @app.route('/v1/command-logs', methods=['POST'])
    def log_command():
        data = request.json
        try:
            success = db_manager.log_command(data['user_id'], data['command'])
            if success:
                return format_response(data={'success': True})
            return format_response(
                errors=[{'code': 'LoggingFailed', 'message': 'Failed to log command'}],
                status_code=400
            )
        except Exception as e:
            return format_response(
                errors=[{'code': 'InternalServerError', 'message': str(e)}],
                status_code=500
            )

    @app.route('/v1/users/<int:user_id>/favorite-cryptos', methods=['POST'])
    def add_favorite(user_id):
        data = request.json
        try:
            success = db_manager.add_favorite_crypto(user_id, data['crypto_symbol'])
            if success:
                return format_response(
                    data={'user_id': user_id, 'crypto_symbol': data['crypto_symbol']},
                    status_code=201
                )
            return format_response(
                errors=[{'code': 'AlreadyExists', 'message': 'Crypto already in favorites'}],
                status_code=400
            )
        except Exception as e:
            return format_response(
                errors=[{'code': 'InternalServerError', 'message': str(e)}],
                status_code=500
            )

    @app.route('/v1/users/<int:user_id>/favorite-cryptos/<string:crypto_symbol>', methods=['DELETE'])
    def remove_favorite(user_id, crypto_symbol):
        try:
            success = db_manager.remove_favorite_crypto(user_id, crypto_symbol)
            if success:
                return format_response(data={'success': True}, status_code=200)
            return format_response(
                errors=[{'code': 'NotFound', 'message': 'Favorite not found'}],
                status_code=404
            )
        except Exception as e:
            return format_response(
                errors=[{'code': 'InternalServerError', 'message': str(e)}],
                status_code=500
            )

    @app.route('/v1/users/<int:user_id>/favorite-cryptos', methods=['GET'])
    def get_favorites(user_id):
        try:
            favorites = db_manager.get_favorite_cryptos(user_id)
            if favorites is None:
                return format_response(
                    errors=[{'code': 'NotFound', 'message': 'User not found'}],
                    status_code=404
                )
            return format_response(data={'favorites': favorites})
        except Exception as e:
            return format_response(
                errors=[{'code': 'InternalServerError', 'message': str(e)}],
                status_code=500
            )

    @app.route('/v1/stats/popular-cryptos', methods=['GET'])
    def popular_cryptos():
        try:
            limit = request.args.get('limit', default=5, type=int)
            cryptos = db_manager.get_popular_cryptos(limit)
            return format_response(
                data={'cryptos': cryptos},
                meta={'limit': limit}
            )
        except Exception as e:
            return format_response(
                errors=[{'code': 'InternalServerError', 'message': str(e)}],
                status_code=500
            )

    @app.route('/v1/users/unblocked', methods=['GET'])
    def unblocked_users():
        try:
            users = db_manager.get_unblocked_users()
            return format_response(data={'users': users})
        except Exception as e:
            return format_response(
                errors=[{'code': 'InternalServerError', 'message': str(e)}],
                status_code=500
            )

    @app.route('/v1/users/<int:user_id>/block', methods=['POST'])
    def block_user(user_id):
        """Блокировка пользователя"""
        try:
            success = db_manager.block_user(user_id)
            if success:
                return format_response(
                    data={
                        'user_id': user_id,
                        'is_blocked': True,
                        'action': 'blocked'
                    },
                    status_code=200
                )
            return format_response(
                errors=[{
                    'code': 'UserNotFound',
                    'message': f'User {user_id} not found'
                }],
                status_code=404
            )
        except Exception as e:
            return format_response(
                errors=[{'code': 'InternalServerError', 'message': str(e)}],
                status_code=500
            )

    @app.route('/v1/users/<int:user_id>/unblock', methods=['POST'])
    def unblock_user(user_id):
        """Разблокировка пользователя"""
        try:
            success = db_manager.unblock_user(user_id)
            if success:
                return format_response(
                    data={
                        'user_id': user_id,
                        'is_blocked': False,
                        'action': 'unblocked'
                    },
                    status_code=200
                )
            return format_response(
                errors=[{
                    'code': 'UserNotFound',
                    'message': f'User {user_id} not found'
                }],
                status_code=404
            )
        except Exception as e:
            return format_response(
                errors=[{'code': 'InternalServerError', 'message': str(e)}],
                status_code=500
            )

    @app.route('/v1/users/<int:user_id>/block-status', methods=['GET'])
    def is_blocked(user_id):
        try:
            blocked = db_manager.is_blocked(user_id)
            if blocked is None:
                return format_response(
                    errors=[{
                        'code': 'UserNotFound',
                        'message': f'User {user_id} not found'
                    }],
                    status_code=404
                )
            return format_response(data={'user_id': user_id, 'is_blocked': blocked})

        except Exception as e:
            return format_response(
                errors=[{'code': 'InternalServerError', 'message': str(e)}],
                status_code=500
            )

    @app.errorhandler(404)
    def not_found(error):
        return format_response(
            errors=[{'code': 'NotFound', 'message': 'Resource not found'}],
            status_code=404
        )

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5001)