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

Once a tournament is in progress, the organizer calls pair_current_round to
create the games for the current round (round robin only for now), and
record_result to enter the result of each game.
"""

from typing import Literal
from uuid import uuid4

from app.models import Game, Tournament, TournamentStatus
from app.repositories.game_repository import GameRepository
from app.repositories.tournament_repository import TournamentRepository
from app.services.pairing import round_robin_pairings

MIN_PLAYERS_TO_START = 2

# The results an organizer can enter for a played game. "bye" is not here:
# byes get their result automatically when the round is paired.
# A forfeit (a player didn't show up) is entered as a win for the other
# player, "1-0" or "0-1" (decided in issue #17).
PLAYABLE_RESULTS = ("1-0", "0-1", "1/2-1/2")


class TournamentService:
    def __init__(
        self,
        repository: TournamentRepository | None = None,
        game_repository: GameRepository | None = None,
    ) -> None:
        # self.repository is the tournament repository; self.game_repository
        # stores the games. Tests pass in repositories that write to a temporary folder.
        # Without them, the real data/tournaments.json and data/games.json are used.
        self.repository = repository or TournamentRepository()
        self.game_repository = game_repository or GameRepository()

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
        player_ids a second time (decided in issue #13). That means they keep
        their original place in player_ids, rather than moving to the end.

        Raises ValueError if registration isn't open, the player is already
        registered and still active (not withdrawn), or the tournament is full. Only active (not withdrawn)
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
        This doesn't create any games: the organizer pairs round 1 separately
        with pair_current_round (decided in issue #14).
        """
        tournament = self.get_tournament(tournament_id)
        self._require_status(tournament, TournamentStatus.REGISTRATION_OPEN, "start")
        if len(tournament.active_player_ids) < MIN_PLAYERS_TO_START:
            raise ValueError(f"need at least {MIN_PLAYERS_TO_START} players to start")

        tournament.status = TournamentStatus.IN_PROGRESS
        tournament.current_round = 1
        self.repository.update(tournament)
        return tournament

    def pair_current_round(self, tournament_id: str) -> list[Game]:
        """Create and save the games for the tournament's current round.

        Each pair from round_robin_pairings becomes one Game with no result
        yet. A bye is saved as black_id=None and result="bye", as the Game
        model requires. Returns the new games in board order.

        Raises ValueError if the tournament isn't in progress, isn't a round
        robin (Swiss pairing isn't built yet), or the current round already
        has games (pairing twice would create duplicate games).
        """
        tournament = self.get_tournament(tournament_id)
        self._require_status(tournament, TournamentStatus.IN_PROGRESS, "pair round")
        if tournament.format != "round_robin":
            raise ValueError(f"cannot pair round: {tournament.format} pairing is not supported yet")
        round_number = tournament.current_round
        if self.game_repository.list_by_tournament(tournament.id, round=round_number):
            raise ValueError(f"round {round_number} has already been paired")

        # round_robin_pairings leaves out withdrawn players itself.
        pairs = round_robin_pairings(tournament.player_ids, round_number, tournament.withdrawn_ids)
        games = [
            Game(
                id=uuid4().hex,
                tournament_id=tournament.id,
                round=round_number,
                white_id=white_id,
                black_id=black_id,
                result="bye" if black_id is None else None,
            )
            for white_id, black_id in pairs
        ]
        # One write for the whole round, so it can't end up half-saved.
        self.game_repository.add_many(games)
        return games

    def record_result(self, game_id: str, result: str) -> Game:
        """Enter (or correct) the result of a game and save it.

        result must be "1-0" (white won), "0-1" (black won) or "1/2-1/2"
        (draw). Decided in issue #17:
        - A result can be changed: calling this again on the same game
          replaces the old result (e.g. the organizer typed the wrong one).
        - Results can be entered for any round that has been paired, not
          only the current one.
        - Forfeits use "1-0" / "0-1".

        Raises ValueError if the result isn't one of those three, the game
        doesn't exist, the game is a bye, or its tournament isn't in progress.
        """
        if result not in PLAYABLE_RESULTS:
            raise ValueError(
                f"invalid result {result!r}: it must be one of {', '.join(PLAYABLE_RESULTS)}"
            )
        game = self.game_repository.get_by_id(game_id)
        if game is None:
            raise ValueError(f"no game with id {game_id!r}")
        if game.black_id is None:
            raise ValueError("cannot record a result for a bye")
        tournament = self.get_tournament(game.tournament_id)
        self._require_status(tournament, TournamentStatus.IN_PROGRESS, "record result")

        game.result = result
        self.game_repository.update(game)
        return game
