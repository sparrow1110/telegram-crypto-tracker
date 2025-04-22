from flask import Flask, jsonify
from .crypto_parser import CryptoParser
from flasgger import Swagger
from .price_cache import get_cached_prices, get_cached_coin_info
import time
import threading
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
swagger = Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "Crypto Service API",
        "description": "API для получения данных о криптовалютах",
        "version": "1.0.0"
    },
    "consumes": [
        "application/json"
    ],
    "produces": [
        "application/json"
    ]
})
parser = CryptoParser()


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

def scheduled_parsing():
    while True:
        parser.parse_crypto_prices()
        time.sleep(300)  # 5 minutes


@app.route('/v1/crypto-prices', methods=['GET'])
def get_prices():
    """
    Получает текущие цены криптовалют
    ---
    tags:
      - Crypto
    responses:
      200:
        description: Текущие цены криптовалют
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                last_updated:
                  type: string
                  format: date-time
                  example: "2023-05-15 12:34:56"
                BTC:
                  type: object
                  properties:
                    name:
                      type: string
                      example: Bitcoin
                    price_usd:
                      type: number
                      format: float
                      example: 50000.1234
                    percent_change_1h:
                      type: number
                      format: float
                      example: 0.5
                    percent_change_24h:
                      type: number
                      format: float
                      example: -2.3
                    percent_change_7d:
                      type: number
                      format: float
                      example: 5.7
                    market_cap_usd:
                      type: number
                      format: float
                      example: 950000000000
                    rank:
                      type: integer
                      example: 1
                ETH:
                  type: object
                  properties:
                    name:
                      type: string
                      example: Ethereum
                    price_usd:
                      type: number
                      format: float
                      example: 3000.50
                    percent_change_1h:
                      type: number
                      format: float
                      example: 0.2
                    percent_change_24h:
                      type: number
                      format: float
                      example: -1.5
                    percent_change_7d:
                      type: number
                      format: float
                      example: 3.2
                    market_cap_usd:
                      type: number
                      format: float
                      example: 350000000000
                    rank:
                      type: integer
                      example: 2
      503:
        description: Сервис временно недоступен
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
                    example: ServiceUnavailable
                  message:
                    type: string
                    example: "Failed to get crypto prices"
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
                    example: "API request failed"
    """
    try:
        data = get_cached_prices()
        if not data:
            return format_response(
                errors=[{'code': 'ServiceUnavailable', 'message': 'Failed to get crypto prices'}],
                status_code=503
            )
        return format_response(data=data)
    except Exception as e:
        return format_response(
            errors=[{'code': 'InternalServerError', 'message': str(e)}],
            status_code=500
        )


@app.route('/v1/crypto-prices/<string:symbol>', methods=['GET'])
def get_coin(symbol):
    """
    Получает информацию о конкретной криптовалюте
    ---
    tags:
      - Crypto
    parameters:
      - name: symbol
        in: path
        type: string
        required: true
        description: Символ криптовалюты (например, BTC)
    responses:
      200:
        description: Информация о криптовалюте
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                name:
                  type: string
                  example: Bitcoin
                price_usd:
                  type: number
                  format: float
                  example: 50000.1234
                percent_change_1h:
                  type: number
                  format: float
                  example: 0.5
                percent_change_24h:
                  type: number
                  format: float
                  example: -2.3
                percent_change_7d:
                  type: number
                  format: float
                  example: 5.7
                market_cap_usd:
                  type: number
                  format: float
                  example: 950000000000
                rank:
                  type: integer
                  example: 1
                last_updated:
                  type: string
                  format: date-time
                  example: "2023-05-15 12:34:56"
      404:
        description: Криптовалюта не найдена
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
                    example: "Crypto not found"
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
                    example: "Failed to parse crypto data"
    """
    try:
        coin_info = get_cached_coin_info(symbol)
        if not coin_info:
            return format_response(
                errors=[{'code': 'NotFound', 'message': 'Crypto not found'}],
                status_code=404
            )
        if 'error' in coin_info:
            return format_response(
                data=None,
                errors=[{
                    'code': 'NotFound',
                    'message': coin_info['error']
                }],
                status_code=404
            )
        return format_response(data=coin_info)
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
    # Start background thread for scheduled parsing
    scheduler_thread = threading.Thread(target=scheduled_parsing)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    app.run(host='0.0.0.0', port=5003)