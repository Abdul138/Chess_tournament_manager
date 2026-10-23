from app.models import User


def test_save_and_load_users(user_repo):
    users = [
        User(id="u1", username="magnus", password_hash="hashed", role="player", rating=2800),
        User(id="u2", username="org", password_hash="hashed", role="organizer"),
    ]

    user_repo.save_all(users)
    loaded = user_repo.load_all()

    assert loaded == users
