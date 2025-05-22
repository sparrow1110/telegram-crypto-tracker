import pytest
from user_service.app import create_app
from user_service.models import db as user_db
from dotenv import load_dotenv
import os

load_dotenv()

# Устанавливаем REDIS_HOST для тестов
os.environ['REDIS_HOST'] = '172.21.18.121'
os.environ['REDIS_PORT'] = '6379'


@pytest.fixture(scope='module')
def app():
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    }

    app = create_app(test_config)

    with app.app_context():
        user_db.create_all()

    yield app

    with app.app_context():
        user_db.session.remove()
        user_db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
