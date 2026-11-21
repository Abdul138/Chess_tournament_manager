from pathlib import Path

from app.config import DATA_DIR
from app.models import Tournament
from app.repositories.base import BaseRepository


class TournamentRepository(BaseRepository[Tournament]):
    """Reads and writes tournaments in tournaments.json."""

    def __init__(self, file_path: Path = DATA_DIR / "tournaments.json") -> None:
        super().__init__(file_path, Tournament)

    def get_by_id(self, tournament_id: str) -> Tournament | None:
        for tournament in self.load_all():
            if tournament.id == tournament_id:
                return tournament
        return None

    def add(self, tournament: Tournament) -> None:
        tournaments = self.load_all()
        tournaments.append(tournament)
        self.save_all(tournaments)

    def update(self, tournament: Tournament) -> None:
        """Replace the stored tournament that has the same id.

        Raises ValueError if there is no tournament with that id.
        """
        tournaments = self.load_all()
        for index, existing in enumerate(tournaments):
            if existing.id == tournament.id:
                tournaments[index] = tournament
                self.save_all(tournaments)
                return
        raise ValueError(f"no tournament with id {tournament.id!r}")
