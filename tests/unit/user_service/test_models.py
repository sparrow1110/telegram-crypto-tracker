from datetime import datetime
from user_service.models import User, UserFavorite, UsageStat, db


def test_user_model(app):
    with app.app_context():
        # Удаляем все существующие записи перед тестом
        db.session.query(User).delete()
        db.session.commit()

        user = User(
            user_id=123,
            username='testuser',
            first_name='Test',
            last_name='User',
            is_blocked=False
        )
        db.session.add(user)
        db.session.commit()

        # Проверяем, что пользователь создан
        assert user.user_id == 123
        assert user.username == 'testuser'
        assert user.first_name == 'Test'
        assert user.last_name == 'User'
        assert user.is_blocked is False
        assert isinstance(user.join_date, datetime)
        assert isinstance(user.last_activity, datetime)


def test_user_favorite_model(app):
    with app.app_context():
        # Удаляем все существующие записи перед тестом
        db.session.query(UserFavorite).delete()
        db.session.query(User).delete()
        db.session.commit()

        # Создаем пользователя с другим ID
        user = User(
            user_id=124,
            username='testuser2',
            first_name='Test2',
            last_name='User2'
        )
        db.session.add(user)
        db.session.commit()

        # Создаем избранное
        favorite = UserFavorite(
            user_id=124,
            crypto_symbol='BTC'
        )
        db.session.add(favorite)
        db.session.commit()

        # Проверяем
        assert favorite.user_id == 124
        assert favorite.crypto_symbol == 'BTC'
        assert isinstance(favorite.added_on, datetime)


def test_usage_stat_model(app):
    with app.app_context():
        # Удаляем все существующие записи перед тестом
        db.session.query(UsageStat).delete()
        db.session.query(User).delete()
        db.session.commit()

        # Создаем пользователя с другим ID
        user = User(
            user_id=125,
            username='testuser3',
            first_name='Test3',
            last_name='User3'
        )
        db.session.add(user)
        db.session.commit()

        # Создаем запись статистики
        stat = UsageStat(
            user_id=125,
            command='/start'
        )
        db.session.add(stat)
        db.session.commit()

        # Проверяем
        assert stat.user_id == 125
        assert stat.command == '/start'
        assert isinstance(stat.timestamp, datetime)
