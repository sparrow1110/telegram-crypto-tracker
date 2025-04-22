from flask import Flask, jsonify, request
from flasgger import Swagger
from .admin_panel import AdminPanel
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
swagger = Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "Admin Service API",
        "description": "API для администрирования криптобота",
        "version": "1.0.0"
    },
    "consumes": [
        "application/json"
    ],
    "produces": [
        "application/json"
    ]
})
admin = AdminPanel(
    user_service_url=f"http://localhost:{os.getenv('USER_SERVICE_PORT')}",
    crypto_service_url=f"http://localhost:{os.getenv('CRYPTO_SERVICE_PORT')}"
)

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

@app.route('/v1/admins/<int:user_id>/status', methods=['GET'])
def is_admin(user_id):
    """
    Проверяет, является ли пользователь администратором
    ---
    tags:
      - Admin
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID пользователя
    responses:
      200:
        description: Результат проверки
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                is_admin:
                  type: boolean
                  description: Является ли пользователь администратором
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
                    example: "Error connecting to database"
    """
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
    """
    Получает статистику бота
    ---
    tags:
      - Stats
    responses:
      200:
        description: Статистика бота
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                stats:
                  type: string
                  description: Форматированная статистика
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
                    example: "Failed to fetch statistics"
    """
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
    """
    Получает список популярных криптовалют
    ---
    tags:
      - Stats
    responses:
      200:
        description: Популярные криптовалюты
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                popular:
                  type: string
                  description: Форматированный список популярных криптовалют
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
                    example: "Failed to fetch popular cryptos"
    """
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
    """
    Блокирует пользователя
    ---
    tags:
      - Users
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID пользователя
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
                  example: true
                action:
                  type: string
                  example: "admin_blocked"
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
                    example: "Database connection error"
    """
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
            errors=[{'code': 'InternalServerError', 'message': str(e)}],
            status_code=500
        )

@app.route('/v1/users/<int:user_id>/unblock', methods=['POST'])
def unblock_user(user_id):
    """
    Разблокирует пользователя
    ---
    tags:
      - Users
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID пользователя
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
                  example: false
                action:
                  type: string
                  example: "admin_unblocked"
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
                    example: "Database connection error"

    """
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
    app.run(host='0.0.0.0', port=5002)