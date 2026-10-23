from app.models import User


def test_save_and_load_users(user_repo):
    users = [
        User(id="u1", username="magnus", password_hash="hashed", role="player", rating=2800),
        User(id="u2", username="org", password_hash="hashed", role="organizer"),
    ]

    user_repo.save_all(users)
    loaded = user_repo.load_all()

    assert loaded == users


def test_load_missing_file_creates_empty_list(user_repo):
    assert not user_repo.file_path.exists()

    assert user_repo.load_all() == []
    assert user_repo.file_path.read_text(encoding="utf-8") == "[]"


def test_load_empty_list_returns_empty_list(user_repo):
    user_repo.file_path.write_text("[]", encoding="utf-8")

    assert user_repo.load_all() == []


def test_save_twice_replaces_contents(user_repo):
    first = [User(id="u1", username="magnus", password_hash="hashed", role="player")]
    second = [User(id="u2", username="hikaru", password_hash="hashed", role="player")]

    user_repo.save_all(first)
    user_repo.save_all(second)

    assert user_repo.load_all() == second
