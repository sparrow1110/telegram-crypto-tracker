from flask import Flask, jsonify, request
from flasgger import Swagger
from user_service.models import db
from user_service.db_handler import DatabaseManager
import os
from dotenv import load_dotenv

load_dotenv()
db_manager = DatabaseManager()

def create_app(test_config=None):
    app = Flask(__name__)
    swagger = Swagger(app, template={
        "swagger": "2.0",
        "info": {
            "title": "User Service API",
            "description": "API для управления пользователями криптобота",
            "version": "1.0.0"
        },
        "consumes": [
            "application/json"
        ],
        "produces": [
            "application/json"
        ]
    })

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
        """
        Получает статистику пользователей
        ---
        tags:
          - Stats
        responses:
          200:
            description: Статистика пользователей
            schema:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    user_count:
                      type: integer
                      description: Общее количество пользователей
                      example: 4
                    active_users_24h:
                      type: integer
                      description: Количество активных пользователей за 24 часа
                      example: 3
                    active_users_7d:
                      type: integer
                      description: Количество активных пользователей за 7 дней
                      example: 4
                    blocked_count:
                      type: integer
                      description: Количество заблокированных пользователей
                      example: 0
                    favorites_count:
                      type: integer
                      description: Общее количество избранных криптовалют
                      example: 2
                    popular_commands:
                      type: array
                      description: Популярные команды за последние 7 дней
                      items:
                        type: array
                        items:
                          oneOf:
                            - type: string
                            - type: integer
                        example: ["/search", 7]
                      example: [["/search", 7], ["/prices", 6], ["/top5", 6]]
          500:
            description: Ошибка сервера
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: InternalServerError
                      message:
                        type: string
                        example: "Database connection error"
        """
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
        """
        Регистрирует нового пользователя
        ---
        tags:
          - Users
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - user_id
              properties:
                user_id:
                  type: integer
                username:
                  type: string
                first_name:
                  type: string
                last_name:
                  type: string
        responses:
          200:
            description: Информация о пользователе обновлена
            schema:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    user_id:
                      type: integer
                      example: 1
                    username:
                      type: string
                      example: "string"
                    is_new:
                      type: boolean
                      example: false
          201:
            description: Пользователь создан
            schema:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    user_id:
                      type: integer
                    username:
                      type: string
                    is_new:
                      type: boolean
          400:
            description: Ошибка регистрации
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: RegistrationFailed
                      message:
                        type: string
                        example: "User registration failed"
          500:
            description: Ошибка сервера
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: InternalServerError
                      message:
                        type: string
                        example: "Database connection error"
        """
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
        """
        Логирует команду пользователя
        ---
        tags:
          - Logs
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - user_id
                - command
              properties:
                user_id:
                  type: integer
                  example: 1
                command:
                  type: string
                  example: "/prices"
        responses:
          200:
            description: Команда залогирована
            schema:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    success:
                      type: boolean
                      example: true
          400:
            description: Ошибка валидации
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: ValidationError
                      message:
                        type: string
                        example: "Missing required field: command"
          500:
            description: Ошибка сервера
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: InternalServerError
                      message:
                        type: string
                        example: "Failed to log command"
        """
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
        """
        Добавляет криптовалюту в избранное пользователя
        ---
        tags:
          - Favorites
        parameters:
          - name: user_id
            in: path
            type: integer
            required: true
            example: 123456789
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - crypto_symbol
              properties:
                crypto_symbol:
                  type: string
                  example: "BTC"
        responses:
          201:
            description: Криптовалюта добавлена в избранное
            schema:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    user_id:
                      type: integer
                      example: 123456789
                    crypto_symbol:
                      type: string
                      example: "BTC"
          400:
            description: Криптовалюта уже в избранном
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: AlreadyExists
                      message:
                        type: string
                        example: "Crypto already in favorites"
          500:
            description: Ошибка сервера
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: InternalServerError
                      message:
                        type: string
                        example: "Failed to add favorite"
        """
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
        """
        Удаляет криптовалюту из избранного пользователя
        ---
        tags:
          - Favorites
        parameters:
          - name: user_id
            in: path
            type: integer
            required: true
          - name: crypto_symbol
            in: path
            type: string
            required: true
        responses:
          200:
            description: Криптовалюта удалена из избранного
            schema:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    success:
                      type: boolean
          404:
            description: Криптовалюта не найдена в избранном
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: NotFound
                      message:
                        type: string
                        example: "Favorite not found"
          500:
            description: Ошибка сервера
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: InternalServerError
                      message:
                        type: string
                        example: "Database operation failed"
        """
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
        """
        Получает список избранных криптовалют пользователя
        ---
        tags:
          - Favorites
        parameters:
          - name: user_id
            in: path
            type: integer
            required: true
            example: 123456789
        responses:
          200:
            description: Список избранных криптовалют
            schema:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    favorites:
                      type: array
                      items:
                        type: string
                        example: "BTC"
          404:
            description: Пользователь не найден
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: NotFound
                      message:
                        type: string
                        example: "User not found"
          500:
            description: Ошибка сервера
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: InternalServerError
                      message:
                        type: string
                        example: "Failed to get favorites"
        """
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
        """
        Получает список популярных криптовалют
        ---
        tags:
          - Stats
        parameters:
          - name: limit
            in: query
            type: integer
            default: 5
            description: Количество возвращаемых криптовалют
        responses:
          200:
            description: Популярные криптовалюты
            schema:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    cryptos:
                      type: array
                      items:
                        type: array
                        items:
                          oneOf:
                            - type: string
                            - type: integer
                        example: ["BTC", 150]
                      example: [["SOL", 1], ["ETH", 1]]
                meta:
                  type: object
                  properties:
                    limit:
                      type: integer
                      example: 5
          500:
            description: Ошибка сервера
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: InternalServerError
                      message:
                        type: string
                        example: "Failed to get popular cryptos"
        """
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
        """
        Получает список незаблокированных пользователей
        ---
        tags:
          - Users
        responses:
          200:
            description: Список ID незаблокированных пользователей
            schema:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    users:
                      type: array
                      items:
                        type: integer
                        example: 123456789
          500:
            description: Ошибка сервера
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: InternalServerError
                      message:
                        type: string
                        example: "Failed to get unblocked users"
        """
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
        """
        Блокирует пользователя
        ---
        tags:
          - Users
        parameters:
          - name: user_id
            in: path
            required: true
        responses:
          200:
            description: Пользователь заблокирован
            schema:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    user_id:
                      type: integer
                    is_blocked:
                      type: boolean
                    action:
                      type: string
          404:
            description: Пользователь не найден
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: UserNotFound
                      message:
                        type: string
                        example: "User 123 not found"
          500:
            description: Ошибка сервера
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: InternalServerError
                      message:
                        type: string
                        example: "Failed to update user status"
        """
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
        """
        Разблокировка пользователя
        ---
        tags:
          - Users
        parameters:
          - name: user_id
            in: path
            type: integer
            required: true
        responses:
          200:
            description: Пользователь разблокирован
            schema:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    user_id:
                      type: integer
                    is_blocked:
                      type: boolean
                    action:
                      type: string
          404:
            description: Пользователь не найден
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: UserNotFound
                      message:
                        type: string
                        example: "User 123 not found"
          500:
            description: Ошибка сервера
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: InternalServerError
                      message:
                        type: string
                        example: "Failed to update user status"
        """
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
        """
        Проверяет, заблокирован ли пользователь
        ---
        tags:
          - Users
        parameters:
          - name: user_id
            in: path
            type: integer
            required: true
            example: 123456789
        responses:
          200:
            description: Статус блокировки пользователя
            schema:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    user_id:
                      type: integer
                      example: 123456789
                    is_blocked:
                      type: boolean
                      example: false
          404:
            description: Пользователь не найден
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: UserNotFound
                      message:
                        type: string
                        example: "User 123456789 not found"
          500:
            description: Ошибка сервера
            schema:
              type: object
              properties:
                errors:
                  type: array
                  items:
                    type: object
                    properties:
                      code:
                        type: string
                        example: InternalServerError
                      message:
                        type: string
                        example: "Failed to check block status"
        """
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