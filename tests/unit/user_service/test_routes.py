import json
import os
from dotenv import load_dotenv

load_dotenv()

print(f"API_TOKEN from env: {os.getenv('API_TOKEN')}")


def test_register_user(client):
    token = os.getenv("API_TOKEN", "your-secret-api-token")
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print(f"Headers sent in test: {headers}")
    response = client.post(
        '/v1/users',
        headers={
            'Authorization': f'Bearer {os.getenv("API_TOKEN", "your-secret-api-token")}',
            'Content-Type': 'application/json',
        },
        json={'user_id': 123, 'username': 'testuser', 'first_name': 'Test', 'last_name': 'User', 'requester_id': 123},
    )

    data = json.loads(response.data)
    assert response.status_code == 201
    assert data['data']['user_id'] == 123
    assert data['data']['is_new'] is True


def test_log_command(client):
    # First register a user
    client.post(
        '/v1/users',
        headers={
            'Authorization': f'Bearer {os.getenv("API_TOKEN", "your-secret-api-token")}',
            'Content-Type': 'application/json',
        },
        json={'user_id': 123, 'requester_id': 123},
    )

    response = client.post(
        '/v1/command-logs',
        headers={
            'Authorization': f'Bearer {os.getenv("API_TOKEN", "your-secret-api-token")}',
            'Content-Type': 'application/json',
        },
        json={'user_id': 123, 'command': '/start', 'requester_id': 123},
    )

    data = json.loads(response.data)
    assert response.status_code == 200
    assert data['data']['user_id'] == 123
    assert data['data']['command'] == '/start'


def test_add_favorite_crypto(client):
    client.post(
        '/v1/users',
        headers={
            'Authorization': f'Bearer {os.getenv("API_TOKEN", "your-secret-api-token")}',
            'Content-Type': 'application/json',
        },
        json={'user_id': 123, 'requester_id': 123},
    )

    response = client.post(
        '/v1/users/123/favorite-cryptos',
        headers={
            'Authorization': f'Bearer {os.getenv("API_TOKEN", "your-secret-api-token")}',
            'Content-Type': 'application/json',
        },
        json={'crypto_symbol': 'BTC', 'requester_id': 123},
    )

    data = json.loads(response.data)
    assert response.status_code == 201
    assert data['data']['user_id'] == 123
    assert data['data']['crypto_symbol'] == 'BTC'


def test_get_stats(client):
    # Create some test data
    client.post(
        '/v1/users',
        headers={
            'Authorization': f'Bearer {os.getenv("API_TOKEN", "your-secret-api-token")}',
            'Content-Type': 'application/json',
        },
        json={'user_id': 123, 'requester_id': 123},
    )
    client.post(
        '/v1/command-logs',
        headers={
            'Authorization': f'Bearer {os.getenv("API_TOKEN", "your-secret-api-token")}',
            'Content-Type': 'application/json',
        },
        json={'user_id': 123, 'command': '/start', 'requester_id': 123},
    )
    client.post(
        '/v1/users/123/favorite-cryptos',
        headers={
            'Authorization': f'Bearer {os.getenv("API_TOKEN", "your-secret-api-token")}',
            'Content-Type': 'application/json',
        },
        json={'crypto_symbol': 'BTC', 'requester_id': 123},
    )

    response = client.get(
        '/v1/stats',
        headers={
            'Authorization': f'Bearer {os.getenv("API_TOKEN", "your-secret-api-token")}',
            'Content-Type': 'application/json',
        },
        json={'requester_id': 123},
    )
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['data']['user_count'] == 1
    assert data['data']['favorites_count'] == 1
