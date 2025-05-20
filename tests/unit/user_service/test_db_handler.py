from user_service.db_handler import DatabaseManager
from user_service.models import User, UserFavorite, UsageStat


def test_register_user_new(app):
    with app.app_context():
        db_manager = DatabaseManager()
        success, is_new = db_manager.register_user(123, 'testuser', 'Test', 'User')

        assert success is True
        assert is_new is True

        user = User.query.get(123)
        assert user is not None
        assert user.username == 'testuser'


def test_register_user_existing(app):
    with app.app_context():
        # First registration
        db_manager = DatabaseManager()
        db_manager.register_user(123, 'testuser', 'Test', 'User')

        # Update user
        success, is_new = db_manager.register_user(123, 'updateduser', 'Updated', 'User')

        assert success is True
        assert is_new is False

        user = User.query.get(123)
        assert user.username == 'updateduser'


def test_log_command(app):
    with app.app_context():
        db_manager = DatabaseManager()
        db_manager.register_user(123, 'testuser', 'Test', 'User')

        success = db_manager.log_command(123, '/start')
        assert success is True

        stats = UsageStat.query.filter_by(user_id=123).all()
        assert len(stats) == 1
        assert stats[0].command == '/start'


def test_add_favorite_crypto(app):
    with app.app_context():
        db_manager = DatabaseManager()
        db_manager.register_user(123, 'testuser', 'Test', 'User')

        success = db_manager.add_favorite_crypto(123, 'BTC')
        assert success is True

        favorites = UserFavorite.query.filter_by(user_id=123).all()
        assert len(favorites) == 1
        assert favorites[0].crypto_symbol == 'BTC'


def test_remove_favorite_crypto(app):
    with app.app_context():
        db_manager = DatabaseManager()
        db_manager.register_user(123, 'testuser', 'Test', 'User')
        db_manager.add_favorite_crypto(123, 'BTC')

        success = db_manager.remove_favorite_crypto(123, 'BTC')
        assert success is True

        favorites = UserFavorite.query.filter_by(user_id=123).all()
        assert len(favorites) == 0


def test_get_favorite_cryptos(app):
    with app.app_context():
        db_manager = DatabaseManager()
        db_manager.register_user(123, 'testuser', 'Test', 'User')
        db_manager.add_favorite_crypto(123, 'BTC')
        db_manager.add_favorite_crypto(123, 'ETH')

        favorites = db_manager.get_favorite_cryptos(123)
        assert len(favorites) == 2
        assert 'BTC' in favorites
        assert 'ETH' in favorites


def test_block_unblock_user(app):
    with app.app_context():
        db_manager = DatabaseManager()
        db_manager.register_user(123, 'testuser', 'Test', 'User')

        # Block user
        success = db_manager.block_user(123)
        assert success is True
        assert db_manager.is_blocked(123) is True

        # Unblock user
        success = db_manager.unblock_user(123)
        assert success is True
        assert db_manager.is_blocked(123) is False
