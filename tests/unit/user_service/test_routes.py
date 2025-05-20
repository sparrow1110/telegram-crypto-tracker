import json


def test_register_user(client):
    response = client.post(
        '/v1/users',
        json={
            'user_id': 123,
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )

    data = json.loads(response.data)
    assert response.status_code == 201
    assert data['data']['user_id'] == 123
    assert data['data']['is_new'] is True


def test_log_command(client):
    # First register a user
    client.post(
        '/v1/users',
        json={'user_id': 123}
    )

    response = client.post(
        '/v1/command-logs',
        json={
            'user_id': 123,
            'command': '/start'
        }
    )

    data = json.loads(response.data)
    assert response.status_code == 200
    assert data['data']['user_id'] == 123
    assert data['data']['command'] == '/start'


def test_add_favorite_crypto(client):
    client.post('/v1/users', json={'user_id': 123})

    response = client.post(
        '/v1/users/123/favorite-cryptos',
        json={'crypto_symbol': 'BTC'}
    )

    data = json.loads(response.data)
    assert response.status_code == 201
    assert data['data']['user_id'] == 123
    assert data['data']['crypto_symbol'] == 'BTC'


def test_get_stats(client):
    # Create some test data
    client.post('/v1/users', json={'user_id': 123})
    client.post('/v1/command-logs', json={'user_id': 123, 'command': '/start'})
    client.post('/v1/users/123/favorite-cryptos', json={'crypto_symbol': 'BTC'})

    response = client.get('/v1/stats')
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['data']['user_count'] == 1
    assert data['data']['favorites_count'] == 1