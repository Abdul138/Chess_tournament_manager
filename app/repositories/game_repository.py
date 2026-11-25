from pathlib import Path

from app.config import DATA_DIR
from app.models import Game
from app.repositories.base import BaseRepository


class GameRepository(BaseRepository[Game]):
    """Reads and writes games in games.json."""

    def __init__(self, file_path: Path = DATA_DIR / "games.json") -> None:
        super().__init__(file_path, Game)

    def get_by_id(self, game_id: str) -> Game | None:
        for game in self.load_all():
            if game.id == game_id:
                return game
        return None

    def list_by_tournament(self, tournament_id: str, round: int | None = None) -> list[Game]:
        """Return the games of one tournament, in the order they were saved.

        If round is given, only return the games of that round.
        """
        return [
            game
            for game in self.load_all()
            if game.tournament_id == tournament_id and (round is None or game.round == round)
        ]

    def add(self, game: Game) -> None:
        games = self.load_all()
        games.append(game)
        self.save_all(games)

    def add_many(self, games: list[Game]) -> None:
        """Save several new games with a single write to the file.

        Used when pairing a round: either all of the round's games are
        saved, or (if writing fails) none of them are.
        """
        all_games = self.load_all()
        all_games.extend(games)
        self.save_all(all_games)

    def update(self, game: Game) -> None:
        """Replace the stored game that has the same id (e.g. to record a result).

        Raises ValueError if there is no game with that id.
        """
        games = self.load_all()
        for index, existing in enumerate(games):
            if existing.id == game.id:
                games[index] = game
                self.save_all(games)
                return
        raise ValueError(f"no game with id {game.id!r}")
