import pytest

from app.config import DATA_DIR
from app.models import Game
from app.repositories.game_repository import GameRepository


def make_game(game_id, tournament_id="t1", round=1, white_id="u1", black_id="u2", result=None):
    return Game(
        id=game_id, tournament_id=tournament_id, round=round,
        white_id=white_id, black_id=black_id, result=result,
    )


def test_default_path_is_data_games_json():
    assert GameRepository().file_path == DATA_DIR / "games.json"


def test_add_saves_game(game_repo):
    game = make_game("g1")

    game_repo.add(game)

    assert game_repo.load_all() == [game]


def test_add_many_saves_all_games_after_existing_ones(game_repo):
    existing = make_game("g1")
    game_repo.add(existing)
    new = [make_game("g2", round=2), make_game("g3", round=2, white_id="u3", black_id=None, result="bye")]

    game_repo.add_many(new)

    assert game_repo.load_all() == [existing, *new]


def test_add_keeps_existing_games(game_repo):
    first = make_game("g1")
    second = make_game("g2", white_id="u3", black_id="u4")

    game_repo.add(first)
    game_repo.add(second)

    assert game_repo.load_all() == [first, second]


def test_bye_survives_round_trip(game_repo):
    bye = make_game("g1", black_id=None, result="bye")

    game_repo.add(bye)

    assert game_repo.get_by_id("g1") == bye


def test_get_by_id_finds_game(game_repo):
    game_repo.save_all([make_game("g1"), make_game("g2", white_id="u3", black_id="u4")])

    assert game_repo.get_by_id("g2") == make_game("g2", white_id="u3", black_id="u4")


def test_get_by_id_missing_returns_none(game_repo):
    game_repo.save_all([make_game("g1")])

    assert game_repo.get_by_id("nope") is None


def test_list_by_tournament(game_repo):
    t1_round1 = make_game("g1", tournament_id="t1", round=1)
    t2_round1 = make_game("g2", tournament_id="t2", round=1)
    t1_round2 = make_game("g3", tournament_id="t1", round=2)
    game_repo.save_all([t1_round1, t2_round1, t1_round2])

    # Only t1's games, in saved order.
    assert game_repo.list_by_tournament("t1") == [t1_round1, t1_round2]


def test_list_by_tournament_and_round(game_repo):
    t1_round1 = make_game("g1", tournament_id="t1", round=1)
    t2_round1 = make_game("g2", tournament_id="t2", round=1)
    t1_round2 = make_game("g3", tournament_id="t1", round=2)
    game_repo.save_all([t1_round1, t2_round1, t1_round2])

    assert game_repo.list_by_tournament("t1", round=2) == [t1_round2]


def test_list_by_tournament_no_games_returns_empty_list(game_repo):
    game_repo.save_all([make_game("g1", tournament_id="t1")])

    assert game_repo.list_by_tournament("t2") == []
    assert game_repo.list_by_tournament("t1", round=5) == []


def test_update_records_result(game_repo):
    game_repo.save_all([make_game("g1"), make_game("g2", white_id="u3", black_id="u4")])
    played = make_game("g1", result="1-0")

    game_repo.update(played)

    # The played game is saved and the other one is untouched (order kept).
    assert game_repo.load_all() == [played, make_game("g2", white_id="u3", black_id="u4")]


def test_update_missing_game_raises(game_repo):
    game_repo.save_all([make_game("g1")])

    with pytest.raises(ValueError):
        game_repo.update(make_game("nope"))

    # Nothing was changed.
    assert game_repo.load_all() == [make_game("g1")]
