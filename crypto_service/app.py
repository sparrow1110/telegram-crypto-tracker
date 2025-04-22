from flask import Flask, jsonify
from .crypto_parser import CryptoParser
from .price_cache import get_cached_prices, get_cached_coin_info
import time
import threading
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
parser = CryptoParser()


def format_response(data=None, errors=None, meta=None, status_code=200):
    response = {
        'data': data,
    }
    if errors:
        response['errors'] = errors
    if meta:
        response['meta'] = meta

    return jsonify(response), status_code

def scheduled_parsing():
    while True:
        parser.parse_crypto_prices()
        time.sleep(300)  # 5 minutes


@app.route('/v1/crypto-prices', methods=['GET'])
def get_prices():
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