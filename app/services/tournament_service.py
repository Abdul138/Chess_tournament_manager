"""Tournament service: the business rules for a tournament's lifecycle.

The service sits between the routes (not built yet) and the repository:

    routes  ->  services  ->  repositories  ->  models

It knows nothing about HTTP. When an action isn't allowed (for example
registering after the tournament has started), it raises ValueError with a
message saying why. The routes will turn that into an HTTP error later.

Permission checks (is this user an organizer?) are left to the routes and
auth layer, as decided in issue #8.

Lifecycle covered so far:

    draft  ->  registration_open  ->  in_progress

Players can register and withdraw only while registration is open.
"""

from typing import Literal
from uuid import uuid4

from app.models import Tournament, TournamentStatus
from app.repositories.tournament_repository import TournamentRepository

MIN_PLAYERS_TO_START = 2


class TournamentService:
    def __init__(self, repository: TournamentRepository | None = None) -> None:
        # Tests pass in a repository that writes to a temporary folder.
        # Without one, the real data/tournaments.json is used.
        self.repository = repository or TournamentRepository()

    # ---------- Helpers ----------

    def get_tournament(self, tournament_id: str) -> Tournament:
        """Return the tournament, or raise ValueError if it doesn't exist."""
        tournament = self.repository.get_by_id(tournament_id)
        if tournament is None:
            raise ValueError(f"no tournament with id {tournament_id!r}")
        return tournament

    @staticmethod
    def _require_status(tournament: Tournament, expected: TournamentStatus, action: str) -> None:
        if tournament.status != expected:
            raise ValueError(
                f"cannot {action}: tournament is {tournament.status.value!r}, "
                f"it must be {expected.value!r}"
            )

    # ---------- Actions ----------

    def create_tournament(
        self,
        name: str,
        organizer_id: str,
        format: Literal["round_robin", "swiss"],
        max_players: int,
        num_rounds: int | None = None,
    ) -> Tournament:
        """Create and save a new tournament. It starts as a draft.

        The Tournament model checks the details (e.g. Swiss needs num_rounds).
        If they're invalid, Pydantic raises ValidationError, which is a kind
        of ValueError.
        """
        tournament = Tournament(
            id=uuid4().hex,  # a random, unique id like "3f2b9c..."
            name=name,
            organizer_id=organizer_id,
            format=format,
            max_players=max_players,
            num_rounds=num_rounds,
        )
        self.repository.add(tournament)
        return tournament

    def open_registration(self, tournament_id: str) -> Tournament:
        """Move a draft tournament to registration_open."""
        tournament = self.get_tournament(tournament_id)
        self._require_status(tournament, TournamentStatus.DRAFT, "open registration")

        tournament.status = TournamentStatus.REGISTRATION_OPEN
        self.repository.update(tournament)
        return tournament

    def register_player(self, tournament_id: str, player_id: str) -> Tournament:
        """Add a player to a tournament whose registration is open.

        A player who withdrew can register again while registration is open:
        they are taken out of withdrawn_ids, and their id is not added to
        player_ids a second time (decided in issue #13).

        Raises ValueError if registration isn't open, the player is already
        registered, or the tournament is full. Only active (not withdrawn)
        players count towards max_players.
        """
        tournament = self.get_tournament(tournament_id)
        self._require_status(tournament, TournamentStatus.REGISTRATION_OPEN, "register")
        if player_id in tournament.active_player_ids:
            raise ValueError(f"player {player_id!r} is already registered")
        if len(tournament.active_player_ids) >= tournament.max_players:
            raise ValueError(f"tournament is full ({tournament.max_players} players)")

        if player_id in tournament.withdrawn_ids:
            # Coming back after withdrawing: their id is still in player_ids.
            tournament.withdrawn_ids.remove(player_id)
        else:
            tournament.player_ids.append(player_id)
        self.repository.update(tournament)
        return tournament

    def withdraw_player(self, tournament_id: str, player_id: str) -> Tournament:
        """Withdraw a registered player while registration is still open.

        The player's id stays in player_ids and is added to withdrawn_ids.
        Withdrawing is only allowed in registration_open, so withdrawn_ids
        can never change once round 1 has started (decided in issues #7 and #13).

        Raises ValueError if registration isn't open, the player isn't
        registered, or the player has already withdrawn.
        """
        tournament = self.get_tournament(tournament_id)
        self._require_status(tournament, TournamentStatus.REGISTRATION_OPEN, "withdraw")
        if player_id not in tournament.player_ids:
            raise ValueError(f"player {player_id!r} is not registered")
        if player_id in tournament.withdrawn_ids:
            raise ValueError(f"player {player_id!r} has already withdrawn")

        tournament.withdrawn_ids.append(player_id)
        self.repository.update(tournament)
        return tournament

    def start_tournament(self, tournament_id: str) -> Tournament:
        """Move a tournament from registration_open to in_progress, at round 1.

        Needs at least MIN_PLAYERS_TO_START active (not withdrawn) players.
        Pairing round 1 and saving its games is a separate step (not built yet).
        """
        tournament = self.get_tournament(tournament_id)
        self._require_status(tournament, TournamentStatus.REGISTRATION_OPEN, "start")
        if len(tournament.active_player_ids) < MIN_PLAYERS_TO_START:
            raise ValueError(f"need at least {MIN_PLAYERS_TO_START} players to start")

        tournament.status = TournamentStatus.IN_PROGRESS
        tournament.current_round = 1
        self.repository.update(tournament)
        return tournament
