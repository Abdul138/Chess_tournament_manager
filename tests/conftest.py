import pytest

from app.repositories.tournament_repository import TournamentRepository
from app.repositories.user_repository import UserRepository


@pytest.fixture
def user_repo(tmp_path):
    """A user repository that writes to a temporary folder, not the real data/."""
    return UserRepository(tmp_path / "users.json")


@pytest.fixture
def tournament_repo(tmp_path):
    """A tournament repository that writes to a temporary folder, not the real data/."""
    return TournamentRepository(tmp_path / "tournaments.json")
