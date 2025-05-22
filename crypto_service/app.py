from flask import Flask, jsonify
from .crypto_parser import CryptoParser
from flasgger import Swagger, swag_from
from .price_cache import get_cached_prices, get_cached_coin_info
import time
import threading

app = Flask(__name__)
swagger = Swagger(
    app,
    template={
        "swagger": "2.0",
        "info": {
            "title": "Crypto Service API",
            "description": "API для получения данных о криптовалютах",
            "version": "1.0.0",
        },
        "consumes": ["application/json"],
        "produces": ["application/json"],
    },
)
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
        parser.fetch_and_save_crypto_prices()
        time.sleep(300)  # 5 minutes


@app.route('/v1/crypto-prices', methods=['GET'])
@swag_from('docs/get_prices.yaml')
def get_prices():
    try:
        data = get_cached_prices()
        if not data:
            return format_response(
                errors=[{'code': 'ServiceUnavailable', 'message': 'Failed to get crypto prices'}], status_code=503
            )
        return format_response(data=data)
    except Exception as e:
        return format_response(errors=[{'code': 'InternalServerError', 'message': str(e)}], status_code=500)


@app.route('/v1/crypto-prices/<string:symbol>', methods=['GET'])
@swag_from('docs/get_coin.yaml')
def get_coin(symbol):
    try:
        coin_info = get_cached_coin_info(symbol)
        if not coin_info:
            return format_response(errors=[{'code': 'NotFound', 'message': 'Crypto not found'}], status_code=404)
        if 'error' in coin_info:
            return format_response(
                data=None, errors=[{'code': 'NotFound', 'message': coin_info['error']}], status_code=404
            )
        return format_response(data=coin_info)
    except Exception as e:
        return format_response(errors=[{'code': 'InternalServerError', 'message': str(e)}], status_code=500)


@app.errorhandler(404)
def not_found(error):
    return format_response(errors=[{'code': 'NotFound', 'message': 'Resource not found'}], status_code=404)


scheduler_thread = threading.Thread(target=scheduled_parsing)
scheduler_thread.daemon = True
scheduler_thread.start()

if __name__ == '__main__':
    # Start background thread for scheduled parsing
    scheduler_thread = threading.Thread(target=scheduled_parsing)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    app.run(host='0.0.0.0', port=5003)
