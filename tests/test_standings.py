import pytest

from app.models import Game
from app.services.standings import Standing, calculate_standings


# ---------- Helpers ----------

def game(white, black, result, round=1):
    """Build a Game quickly. black=None with result="bye" makes a bye."""
    return Game(
        id=f"{white}-{black}-{round}", tournament_id="t1", round=round,
        white_id=white, black_id=black, result=result,
    )


def by_player(standings):
    return {row.player_id: row for row in standings}


def order(standings):
    return [row.player_id for row in standings]


def ranks(standings):
    return [row.rank for row in standings]


# ---------- Points ----------

def test_win_draw_loss_points():
    standings = calculate_standings(
        ["a", "b", "c"],
        [game("a", "b", "1-0"), game("b", "c", "1/2-1/2", round=2), game("c", "a", "0-1", round=3)],
    )

    rows = by_player(standings)
    assert rows["a"].points == 2
    assert rows["b"].points == 0.5
    assert rows["c"].points == 0.5


def test_bye_gives_one_point():
    standings = calculate_standings(["a", "b"], [game("a", None, "bye")])

    assert by_player(standings)["a"].points == 1


def test_bye_is_not_a_win_and_adds_no_sonneborn_berger():
    # a: bye + beat b = 2 points. b: lost to a + bye = 1 point.
    games = [
        game("a", None, "bye"),
        game("b", "a", "0-1", round=2),
        game("b", None, "bye", round=3),
    ]
    rows = by_player(calculate_standings(["a", "b"], games))

    assert (rows["a"].points, rows["b"].points) == (2, 1)
    assert rows["a"].wins == 1  # only the real game, not the bye
    assert rows["a"].sonneborn_berger == 1  # b's 1 point; the bye adds nothing
    assert rows["b"].sonneborn_berger == 0  # b's only real game was a loss


def test_unplayed_games_are_ignored():
    standings = calculate_standings(["a", "b"], [game("a", "b", None)])

    assert all(row.points == 0 and row.wins == 0 for row in standings)
    assert ranks(standings) == [1, 1]


def test_no_games_everyone_shares_first_place():
    standings = calculate_standings(["a", "b", "c"], [])

    assert ranks(standings) == [1, 1, 1]
    assert order(standings) == ["a", "b", "c"]  # registration order kept


def test_no_players_returns_empty_list():
    assert calculate_standings([], []) == []


def test_repeated_player_id_raises():
    with pytest.raises(ValueError, match="unique"):
        calculate_standings(["a", "a"], [])


def test_returns_standing_rows():
    standings = calculate_standings(["a", "b"], [game("a", "b", "1-0")])

    assert standings == [
        Standing(rank=1, player_id="a", points=1, head_to_head=0, sonneborn_berger=0, wins=1),
        Standing(rank=2, player_id="b", points=0, head_to_head=0, sonneborn_berger=0, wins=0),
    ]


# ---------- Ordering ----------

def test_sorted_by_points_highest_first():
    standings = calculate_standings(
        ["c", "b", "a"],
        [game("a", "b", "1-0"), game("a", "c", "1-0", round=2), game("b", "c", "1-0", round=3)],
    )

    assert order(standings) == ["a", "b", "c"]
    assert ranks(standings) == [1, 2, 3]


def test_only_listed_players_appear():
    # Withdrawn players are left out by the caller simply not listing them.
    standings = calculate_standings(["a", "b"], [game("a", "b", "1/2-1/2")])

    assert order(standings) == ["a", "b"]


# ---------- Tie-break 1: head-to-head ----------

def test_head_to_head_breaks_a_two_way_tie():
    # Final points: a 2, b 2, c 1, d 1. b beat a, so b is ahead of a.
    games = [
        game("b", "a", "1-0"),
        game("a", "c", "1-0", round=2),
        game("a", "d", "1-0", round=3),
        game("b", "c", "1/2-1/2", round=4),
        game("b", "d", "1/2-1/2", round=5),
        game("c", "d", "1/2-1/2", round=6),
    ]
    standings = calculate_standings(["a", "b", "c", "d"], games)
    rows = by_player(standings)

    assert (rows["a"].points, rows["b"].points) == (2, 2)
    assert (rows["a"].head_to_head, rows["b"].head_to_head) == (0, 1)
    assert order(standings)[:2] == ["b", "a"]
    # c and d (1 point each) drew each other: head-to-head 0.5 each.
    assert rows["c"].head_to_head == rows["d"].head_to_head == 0.5


def test_head_to_head_ignores_games_against_players_with_other_points():
    # a and b end on 1.5 and drew each other. Their wins against c (0 points)
    # are not head-to-head games, so head-to-head is 0.5 each.
    games = [
        game("a", "b", "1/2-1/2"),
        game("a", "c", "1-0", round=2),
        game("c", "b", "0-1", round=3),
    ]
    rows = by_player(calculate_standings(["a", "b", "c"], games))

    assert rows["a"].head_to_head == rows["b"].head_to_head == 0.5
    assert rows["c"].head_to_head == 0


def test_head_to_head_in_a_three_way_tie():
    # Games inside the group of a, b and c:
    #   a beat b, b beat c, a drew c  ->  a 1.5, b 1, c 0.5 inside the group.
    # Outside it: b drew d (+0.5) and c had a bye (+1),
    # so a, b and c all finish on 1.5 and d on 0.5.
    games = [
        game("a", "b", "1-0"),
        game("b", "c", "1-0", round=2),
        game("a", "c", "1/2-1/2", round=3),
        game("b", "d", "1/2-1/2", round=4),
        game("c", None, "bye", round=5),
    ]
    standings = calculate_standings(["c", "b", "a", "d"], games)
    rows = by_player(standings)

    assert [rows[p].points for p in "abcd"] == [1.5, 1.5, 1.5, 0.5]
    assert [rows[p].head_to_head for p in "abc"] == [1.5, 1, 0.5]
    assert order(standings) == ["a", "b", "c", "d"]
    assert ranks(standings) == [1, 2, 3, 4]


def test_head_to_head_splits_off_one_player_then_sonneborn_berger_orders_the_rest():
    # Inside the group of a, b and c: a beat b and c, b and c drew
    # -> head-to-head a 2, b 0.5, c 0.5. Head-to-head is worked out once for
    # the whole group, so b and c are then ordered by Sonneborn-Berger.
    # Outside it: b beat d and drew e, c beat e and drew d, d beat e.
    # Final points: a 2, b 2, c 2, d 1.5, e 0.5.
    # SB b = 1.5 (d) + 2/2 (c) + 0.5/2 (e) = 2.75
    # SB c = 2/2 (b) + 0.5 (e) + 1.5/2 (d) = 2.25
    games = [
        game("a", "b", "1-0"),
        game("a", "c", "1-0", round=2),
        game("b", "c", "1/2-1/2", round=3),
        game("b", "d", "1-0", round=4),
        game("b", "e", "1/2-1/2", round=5),
        game("c", "e", "1-0", round=6),
        game("c", "d", "1/2-1/2", round=7),
        game("d", "e", "1-0", round=8),
    ]
    standings = calculate_standings(["c", "b", "a", "d", "e"], games)
    rows = by_player(standings)

    assert [rows[p].points for p in "abcde"] == [2, 2, 2, 1.5, 0.5]
    assert [rows[p].head_to_head for p in "abc"] == [2, 0.5, 0.5]
    assert (rows["b"].sonneborn_berger, rows["c"].sonneborn_berger) == (2.75, 2.25)
    assert order(standings) == ["a", "b", "c", "d", "e"]
    assert ranks(standings) == [1, 2, 3, 4, 5]


# ---------- Tie-break 2: Sonneborn-Berger ----------

def test_sonneborn_berger_counts_beaten_and_drawn_opponents():
    # Final points: a 1.5, b 1, c 1.5, d 0.
    # a beat b (1 point) and drew c (1.5 points): SB = 1 + 1.5 / 2 = 1.75.
    games = [
        game("a", "b", "1-0"),
        game("a", "c", "1/2-1/2", round=2),
        game("b", "c", "1-0", round=3),
        game("c", "d", "1-0", round=4),
    ]
    rows = by_player(calculate_standings(["a", "b", "c", "d"], games))

    assert [rows[p].points for p in "abcd"] == [1.5, 1, 1.5, 0]
    assert rows["a"].sonneborn_berger == 1.75
    assert rows["d"].sonneborn_berger == 0  # lost its only game


def test_sonneborn_berger_breaks_a_tie_when_head_to_head_is_level():
    # Final points: a 1, b 1, c 1.5, d 0.5.
    # a and b drew each other, so head-to-head is level (0.5 each).
    # a also drew c (1.5 points), b also drew d (0.5 points):
    # SB a = (1 + 1.5) / 2 = 1.25, SB b = (1 + 0.5) / 2 = 0.75, so a is ahead.
    games = [
        game("a", "b", "1/2-1/2"),
        game("a", "c", "1/2-1/2", round=2),
        game("b", "d", "1/2-1/2", round=3),
        game("c", "d", "1-0", round=4),
    ]
    standings = calculate_standings(["b", "a", "c", "d"], games)
    rows = by_player(standings)

    assert rows["a"].points == rows["b"].points == 1
    assert rows["a"].head_to_head == rows["b"].head_to_head == 0.5
    assert (rows["a"].sonneborn_berger, rows["b"].sonneborn_berger) == (1.25, 0.75)
    assert order(standings) == ["c", "a", "b", "d"]


# ---------- Tie-break 3: wins ----------

def test_wins_break_a_tie_when_head_to_head_and_sonneborn_berger_are_level():
    # a and b both end on 1 point and never played each other.
    # a beat x (who ends on 0), so a's SB is 0 and a has 1 win.
    # b's point is a bye: no SB and no win. So a is ahead on wins.
    games = [game("a", "x", "1-0"), game("b", None, "bye")]
    standings = calculate_standings(["b", "a"], games)
    rows = by_player(standings)

    assert rows["a"].points == rows["b"].points == 1
    assert rows["a"].head_to_head == rows["b"].head_to_head == 0
    assert rows["a"].sonneborn_berger == rows["b"].sonneborn_berger == 0
    assert (rows["a"].wins, rows["b"].wins) == (1, 0)
    assert order(standings) == ["a", "b"]
    assert ranks(standings) == [1, 2]


# ---------- Sharing a rank ----------

def test_fully_tied_players_share_a_rank_and_the_next_rank_is_skipped():
    # a and b drew each other and both beat c; everything is level.
    games = [
        game("a", "b", "1/2-1/2"),
        game("a", "c", "1-0", round=2),
        game("c", "b", "0-1", round=3),
    ]
    standings = calculate_standings(["b", "a", "c"], games)

    assert order(standings) == ["b", "a", "c"]  # tied players keep player_ids order
    assert ranks(standings) == [1, 1, 3]


# ---------- TournamentService.get_standings ----------

def start_round_robin(service, player_ids, withdraw=()):
    """Create a round robin, register the players, withdraw some, and start it."""
    tournament = service.create_tournament(
        name="Club RR", organizer_id="o1", format="round_robin", max_players=8,
    )
    service.open_registration(tournament.id)
    for player_id in player_ids:
        service.register_player(tournament.id, player_id)
    for player_id in withdraw:
        service.withdraw_player(tournament.id, player_id)
    return service.start_tournament(tournament.id)


def test_get_standings_uses_recorded_results(tournament_service):
    tournament = start_round_robin(tournament_service, ["u1", "u2", "u3", "u4"])
    games = tournament_service.pair_current_round(tournament.id)
    tournament_service.record_result(games[0].id, "1-0")  # games[1] not played yet

    standings = tournament_service.get_standings(tournament.id)

    winner = games[0].white_id
    assert standings[0].player_id == winner
    assert standings[0].points == 1
    assert sorted(row.player_id for row in standings) == ["u1", "u2", "u3", "u4"]
    assert sum(row.points for row in standings) == 1


def test_get_standings_leaves_out_withdrawn_players(tournament_service):
    tournament = start_round_robin(tournament_service, ["u1", "u2", "u3"], withdraw=["u2"])

    standings = tournament_service.get_standings(tournament.id)

    assert [row.player_id for row in standings] == ["u1", "u3"]


def test_get_standings_counts_a_bye(tournament_service):
    tournament = start_round_robin(tournament_service, ["u1", "u2", "u3"])
    games = tournament_service.pair_current_round(tournament.id)
    bye = next(game for game in games if game.result == "bye")

    standings = tournament_service.get_standings(tournament.id)

    assert standings[0].player_id == bye.white_id
    assert standings[0].points == 1


def test_get_standings_only_counts_its_own_tournament(tournament_service):
    first = start_round_robin(tournament_service, ["u1", "u2"])
    second = start_round_robin(tournament_service, ["u1", "u2"])
    game = tournament_service.pair_current_round(first.id)[0]
    tournament_service.record_result(game.id, "1-0")

    standings = tournament_service.get_standings(second.id)

    assert all(row.points == 0 for row in standings)


def test_get_standings_after_a_whole_round_robin(tournament_service):
    # Four players, three rounds, white wins every game.
    tournament = start_round_robin(tournament_service, ["u1", "u2", "u3", "u4"])
    white_games = {player_id: 0 for player_id in tournament.player_ids}
    for round_number in range(1, tournament.total_rounds + 1):
        for game in tournament_service.pair_current_round(tournament.id):
            tournament_service.record_result(game.id, "1-0")
            white_games[game.white_id] += 1
        if round_number < tournament.total_rounds:
            tournament_service.advance_round(tournament.id)

    standings = tournament_service.get_standings(tournament.id)

    assert sum(row.points for row in standings) == 6  # 6 games, 1 point each
    assert {row.player_id: row.points for row in standings} == white_games
    assert [row.points for row in standings] == sorted(
        (row.points for row in standings), reverse=True
    )


def test_get_standings_unknown_tournament_raises(tournament_service):
    with pytest.raises(ValueError, match="no tournament"):
        tournament_service.get_standings("missing")
