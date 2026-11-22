from collections import Counter
from itertools import combinations

import pytest

from app.services.pairing import round_robin_pairings


def ids(count):
    return [f"u{number}" for number in range(1, count + 1)]


def all_rounds(players, withdrawn_ids=()):
    """Pair every round of a round robin and return them as a list of rounds."""
    active = [p for p in players if p not in withdrawn_ids]
    num_rounds = len(active) - 1 if len(active) % 2 == 0 else len(active)
    return [round_robin_pairings(players, r, withdrawn_ids) for r in range(1, num_rounds + 1)]


# ---------- Small examples ----------

def test_two_players_play_once():
    assert round_robin_pairings(["a", "b"], 1) == [("a", "b")]


def test_three_players_one_bye_per_round():
    rounds = all_rounds(["a", "b", "c"])

    assert len(rounds) == 3
    for pairs in rounds:
        byes = [white for white, black in pairs if black is None]
        assert len(byes) == 1


def test_fewer_than_two_players_returns_empty_list():
    assert round_robin_pairings([], 1) == []
    assert round_robin_pairings(["a"], 1) == []


def test_does_not_change_the_input_list():
    players = ids(5)

    round_robin_pairings(players, 2, withdrawn_ids=["u3"])

    assert players == ids(5)


# ---------- Whole-tournament rules ----------

@pytest.mark.parametrize("count", range(2, 13))
def test_every_pair_meets_exactly_once(count):
    players = ids(count)
    games = Counter()
    for pairs in all_rounds(players):
        for white, black in pairs:
            if black is not None:
                games[frozenset((white, black))] += 1

    assert set(games) == {frozenset(pair) for pair in combinations(players, 2)}
    assert set(games.values()) == {1}


@pytest.mark.parametrize("count", range(2, 13))
def test_each_player_appears_once_per_round(count):
    players = ids(count)
    for pairs in all_rounds(players):
        seated = [p for pair in pairs for p in pair if p is not None]
        assert sorted(seated) == sorted(players)


@pytest.mark.parametrize("count", [3, 5, 7, 9, 11])
def test_odd_count_everyone_gets_exactly_one_bye(count):
    players = ids(count)
    byes = Counter(white for pairs in all_rounds(players) for white, black in pairs if black is None)

    assert byes == Counter({player: 1 for player in players})


@pytest.mark.parametrize("count", range(2, 13))
def test_colours_are_balanced(count):
    """Whites and blacks differ by at most one for every player."""
    whites, blacks = Counter(), Counter()
    for pairs in all_rounds(ids(count)):
        for white, black in pairs:
            if black is not None:
                whites[white] += 1
                blacks[black] += 1

    for player in ids(count):
        assert abs(whites[player] - blacks[player]) <= 1


@pytest.mark.parametrize("count", range(3, 13))
def test_no_long_runs_of_the_same_colour(count):
    """Nobody gets the same colour more than twice in a row (byes are skipped)."""
    history = {player: "" for player in ids(count)}
    for pairs in all_rounds(ids(count)):
        for white, black in pairs:
            if black is not None:
                history[white] += "W"
                history[black] += "B"

    for colours in history.values():
        assert "WWW" not in colours and "BBB" not in colours


# ---------- Withdrawn players ----------

def test_withdrawn_players_are_not_paired():
    pairs = round_robin_pairings(ids(4), 1, withdrawn_ids=["u2"])

    seated = {p for pair in pairs for p in pair}
    assert "u2" not in seated
    # 3 players left: one game and one bye.
    assert len(pairs) == 2
    assert None in seated


def test_withdrawn_players_are_left_out_of_the_whole_schedule():
    rounds = all_rounds(ids(5), withdrawn_ids=["u5"])

    # 4 active players -> 3 rounds of 2 games, no byes.
    assert len(rounds) == 3
    for pairs in rounds:
        assert len(pairs) == 2
        assert all(black is not None for _, black in pairs)
        assert "u5" not in {p for pair in pairs for p in pair}


# ---------- Bad input ----------

@pytest.mark.parametrize("round_number", [0, -1, 4])
def test_round_out_of_range_raises(round_number):
    # 4 players -> rounds 1 to 3.
    with pytest.raises(ValueError):
        round_robin_pairings(ids(4), round_number)


def test_odd_count_last_round_is_allowed():
    # 5 players -> 5 rounds (one extra because of the byes).
    assert len(round_robin_pairings(ids(5), 5)) == 3


def test_duplicate_player_ids_raise():
    with pytest.raises(ValueError):
        round_robin_pairings(["a", "b", "a"], 1)
