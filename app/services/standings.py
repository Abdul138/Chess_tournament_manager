"""Standings: who is winning, worked out from the recorded game results.

Like pairing.py, this module has no files and no HTTP: it takes the players
and the games, and returns the standings. That makes it easy to test.

Rules (decided in issue #20):

- Points: win = 1, draw = 0.5, loss = 0, bye = 1.
- Games with no result yet (result=None) are ignored.
- Withdrawn players are left out. The caller passes only the active players.
- Players with the same points are ordered by these tie-breaks, in order:
    1. Head-to-head: points scored in the games between the tied players.
    2. Sonneborn-Berger: for every opponent you beat, add their points;
       for every opponent you drew with, add half their points.
       (Beating strong players counts for more than beating weak ones.)
    3. Number of wins.
- Players still tied after all three share the same rank, e.g. 1, 2, 2, 4.

Details the issue didn't spell out, chosen here (see the PR for #20):

- Head-to-head is worked out once for each group of players on the same
  points, using only the games played inside that group.
- A bye gives 1 point, but it is not a game against anyone, so it adds
  nothing to Sonneborn-Berger and does not count as a win. (In a finished
  round robin with an odd number of players, everyone gets exactly one bye,
  so this treats everyone the same. Mid-tournament, a player who has
  already had their bye can be a point ahead of someone still waiting for
  theirs.)
"""

from collections import defaultdict
from dataclasses import dataclass

from app.models import Game

# Points each side gets for a result: (white's points, black's points).
RESULT_POINTS = {
    "1-0": (1.0, 0.0),
    "0-1": (0.0, 1.0),
    "1/2-1/2": (0.5, 0.5),
}
BYE_POINTS = 1.0


@dataclass(frozen=True)
class Standing:
    """One row of the standings table.

    head_to_head only means something when compared between players on the
    same points: it counts the points scored against those players.
    """

    rank: int
    player_id: str
    points: float
    head_to_head: float
    sonneborn_berger: float
    wins: int


def calculate_standings(player_ids: list[str], games: list[Game]) -> list[Standing]:
    """Return one Standing per player, best first.

    player_ids should be the active (not withdrawn) players. games can be
    every game of the tournament: unplayed games are skipped. Players with
    exactly the same points and tie-breaks keep their order from player_ids
    and share a rank.

    Raises ValueError if a player id is repeated.
    """
    if len(player_ids) != len(set(player_ids)):
        raise ValueError("player ids must be unique")

    # ---------- Collect each player's results ----------
    points: dict[str, float] = defaultdict(float)
    wins: dict[str, int] = defaultdict(int)
    # (player, opponent, points the player scored) for every played game.
    # Each game appears twice, once from each player's side.
    played: list[tuple[str, str, float]] = []

    for game in games:
        if game.result is None:
            continue  # not played yet
        if game.result == "bye":
            points[game.white_id] += BYE_POINTS
            continue
        white_points, black_points = RESULT_POINTS[game.result]
        points[game.white_id] += white_points
        points[game.black_id] += black_points
        played.append((game.white_id, game.black_id, white_points))
        played.append((game.black_id, game.white_id, black_points))
        if white_points == 1.0:
            wins[game.white_id] += 1
        elif black_points == 1.0:
            wins[game.black_id] += 1

    # ---------- Tie-break 1: head-to-head ----------
    # Players on the same points form a group. Only games played inside a
    # group count towards head-to-head.
    listed = set(player_ids)
    head_to_head: dict[str, float] = defaultdict(float)
    for player, opponent, scored in played:
        both_listed = player in listed and opponent in listed
        if both_listed and points[player] == points[opponent]:
            head_to_head[player] += scored

    # ---------- Tie-break 2: Sonneborn-Berger ----------
    sonneborn_berger: dict[str, float] = defaultdict(float)
    for player, opponent, scored in played:
        # scored is 1 for a win, 0.5 for a draw, 0 for a loss.
        sonneborn_berger[player] += scored * points[opponent]

    # ---------- Sort and rank ----------
    def sort_key(player_id: str) -> tuple[float, float, float, int]:
        return (
            points[player_id],
            head_to_head[player_id],
            sonneborn_berger[player_id],
            wins[player_id],
        )

    # sorted() keeps the original order for equal keys, so fully tied
    # players stay in player_ids order.
    ordered = sorted(player_ids, key=sort_key, reverse=True)

    standings: list[Standing] = []
    for position, player_id in enumerate(ordered, start=1):
        if standings and sort_key(player_id) == sort_key(standings[-1].player_id):
            rank = standings[-1].rank  # fully tied: share the rank above
        else:
            rank = position
        standings.append(
            Standing(
                rank=rank,
                player_id=player_id,
                points=points[player_id],
                head_to_head=head_to_head[player_id],
                sonneborn_berger=sonneborn_berger[player_id],
                wins=wins[player_id],
            )
        )
    return standings
