from app.config import DATA_DIR
from app.models import User
from app.repositories.user_repository import UserRepository


def make_user(user_id, username):
    return User(id=user_id, username=username, password_hash="hashed", role="player")


def test_default_path_is_data_users_json():
    assert UserRepository().file_path == DATA_DIR / "users.json"


def test_add_saves_user(user_repo):
    user = make_user("u1", "magnus")

    user_repo.add(user)

    assert user_repo.load_all() == [user]


def test_add_keeps_existing_users(user_repo):
    first = make_user("u1", "magnus")
    second = make_user("u2", "hikaru")

    user_repo.add(first)
    user_repo.add(second)

    assert user_repo.load_all() == [first, second]


def test_get_by_id_finds_user(user_repo):
    user_repo.save_all([make_user("u1", "magnus"), make_user("u2", "hikaru")])

    assert user_repo.get_by_id("u2") == make_user("u2", "hikaru")


def test_get_by_id_missing_returns_none(user_repo):
    user_repo.save_all([make_user("u1", "magnus")])

    assert user_repo.get_by_id("nope") is None


def test_get_by_username_finds_user(user_repo):
    user_repo.save_all([make_user("u1", "magnus"), make_user("u2", "hikaru")])

    assert user_repo.get_by_username("hikaru") == make_user("u2", "hikaru")


def test_get_by_username_missing_returns_none(user_repo):
    user_repo.save_all([make_user("u1", "magnus")])

    assert user_repo.get_by_username("nope") is None
