import pytest

from app.models import User
from app.repositories.base import BaseRepository


@pytest.fixture
def user_repo(tmp_path):
    """A user repository that writes to a temporary folder, not the real data/."""
    return BaseRepository(tmp_path / "users.json", User)
