import pytest

from app.models import TournamentStatus
from app.repositories.game_repository import GameRepository
from app.repositories.tournament_repository import TournamentRepository
from app.services.pairing import round_robin_pairings
from app.services.tournament_service import TournamentService


# ---------- Helpers ----------

def create_round_robin(service, max_players=4):
    return service.create_tournament(
        name="Club RR", organizer_id="o1", format="round_robin", max_players=max_players,
    )


def open_tournament(service, max_players=4):
    """Create a round robin and open its registration."""
    tournament = create_round_robin(service, max_players)
    return service.open_registration(tournament.id)


def open_with_players(service, player_ids, max_players=4):
    tournament = open_tournament(service, max_players)
    for player_id in player_ids:
        service.register_player(tournament.id, player_id)
    return service.get_tournament(tournament.id)


def started_with_players(service, player_ids, max_players=4):
    """Create a round robin, register the players and start it."""
    tournament = open_with_players(service, player_ids, max_players)
    return service.start_tournament(tournament.id)


# ---------- Setup ----------

def test_default_repository_uses_real_data_folder():
    assert TournamentService().repository.file_path == TournamentRepository().file_path


def test_default_game_repository_uses_real_data_folder():
    assert TournamentService().game_repository.file_path == GameRepository().file_path


# ---------- create_tournament ----------

def test_create_saves_a_draft(tournament_service, tournament_repo):
    tournament = create_round_robin(tournament_service)

    assert tournament.status == TournamentStatus.DRAFT
    assert tournament.player_ids == []
    assert tournament.current_round == 0
    assert tournament_repo.get_by_id(tournament.id) == tournament


def test_create_swiss_keeps_num_rounds(tournament_service):
    tournament = tournament_service.create_tournament(
        name="Open", organizer_id="o1", format="swiss", max_players=16, num_rounds=5,
    )

    assert tournament.num_rounds == 5


def test_create_gives_each_tournament_a_different_id(tournament_service):
    first = create_round_robin(tournament_service)
    second = create_round_robin(tournament_service)

    assert first.id != second.id
    assert len(first.id) == 32  # uuid4().hex is 32 hex characters


def test_create_with_invalid_details_raises_and_saves_nothing(tournament_service, tournament_repo):
    # Swiss without num_rounds is rejected by the Tournament model.
    with pytest.raises(ValueError):
        tournament_service.create_tournament(
            name="Open", organizer_id="o1", format="swiss", max_players=16,
        )

    assert tournament_repo.load_all() == []


# ---------- get_tournament ----------

def test_get_unknown_tournament_raises(tournament_service):
    with pytest.raises(ValueError, match="no tournament"):
        tournament_service.get_tournament("missing")


# ---------- open_registration ----------

def test_open_registration_moves_draft_to_registration_open(tournament_service, tournament_repo):
    tournament = create_round_robin(tournament_service)

    opened = tournament_service.open_registration(tournament.id)

    assert opened.status == TournamentStatus.REGISTRATION_OPEN
    assert tournament_repo.get_by_id(tournament.id).status == TournamentStatus.REGISTRATION_OPEN


def test_open_registration_twice_raises(tournament_service):
    tournament = open_tournament(tournament_service)

    with pytest.raises(ValueError, match="cannot open registration"):
        tournament_service.open_registration(tournament.id)


def test_open_registration_unknown_tournament_raises(tournament_service):
    with pytest.raises(ValueError, match="no tournament"):
        tournament_service.open_registration("missing")


# ---------- register_player ----------

def test_register_adds_player_and_saves(tournament_service, tournament_repo):
    tournament = open_tournament(tournament_service)

    updated = tournament_service.register_player(tournament.id, "u1")

    assert updated.player_ids == ["u1"]
    assert tournament_repo.get_by_id(tournament.id).player_ids == ["u1"]


def test_register_keeps_registration_order(tournament_service):
    tournament = open_with_players(tournament_service, ["u2", "u1", "u3"])

    assert tournament.player_ids == ["u2", "u1", "u3"]


def test_register_while_draft_raises(tournament_service):
    tournament = create_round_robin(tournament_service)

    with pytest.raises(ValueError, match="cannot register"):
        tournament_service.register_player(tournament.id, "u1")


def test_register_after_start_raises(tournament_service):
    tournament = open_with_players(tournament_service, ["u1", "u2"])
    tournament_service.start_tournament(tournament.id)

    with pytest.raises(ValueError, match="cannot register"):
        tournament_service.register_player(tournament.id, "u3")


def test_register_same_player_twice_raises(tournament_service, tournament_repo):
    tournament = open_with_players(tournament_service, ["u1"])

    with pytest.raises(ValueError, match="already registered"):
        tournament_service.register_player(tournament.id, "u1")

    assert tournament_repo.get_by_id(tournament.id).player_ids == ["u1"]


def test_register_when_full_raises(tournament_service, tournament_repo):
    tournament = open_with_players(tournament_service, ["u1", "u2"], max_players=2)

    with pytest.raises(ValueError, match="full"):
        tournament_service.register_player(tournament.id, "u3")

    assert tournament_repo.get_by_id(tournament.id).player_ids == ["u1", "u2"]


def test_withdrawn_players_do_not_count_towards_max_players(tournament_service):
    tournament = open_with_players(tournament_service, ["u1", "u2"], max_players=2)
    tournament_service.withdraw_player(tournament.id, "u2")

    updated = tournament_service.register_player(tournament.id, "u3")

    assert updated.player_ids == ["u1", "u2", "u3"]
    assert updated.active_player_ids == ["u1", "u3"]


def test_withdrawn_player_can_register_again(tournament_service, tournament_repo):
    tournament = open_with_players(tournament_service, ["u1", "u2"])
    tournament_service.withdraw_player(tournament.id, "u1")

    updated = tournament_service.register_player(tournament.id, "u1")

    # Taken out of withdrawn_ids, and not added to player_ids a second time.
    assert updated.player_ids == ["u1", "u2"]
    assert updated.withdrawn_ids == []
    assert tournament_repo.get_by_id(tournament.id) == updated


def test_returning_player_keeps_their_original_place(tournament_service):
    tournament = open_with_players(tournament_service, ["u1", "u2"])
    tournament_service.withdraw_player(tournament.id, "u1")
    tournament_service.register_player(tournament.id, "u3")

    updated = tournament_service.register_player(tournament.id, "u1")

    # u1 comes back in their first spot, not after u3.
    assert updated.active_player_ids == ["u1", "u2", "u3"]


def test_withdraw_register_withdraw_again(tournament_service):
    tournament = open_with_players(tournament_service, ["u1", "u2"])
    tournament_service.withdraw_player(tournament.id, "u1")
    tournament_service.register_player(tournament.id, "u1")

    updated = tournament_service.withdraw_player(tournament.id, "u1")

    assert updated.player_ids == ["u1", "u2"]
    assert updated.withdrawn_ids == ["u1"]


def test_withdrawn_player_registering_again_when_full_raises(tournament_service, tournament_repo):
    tournament = open_with_players(tournament_service, ["u1", "u2"], max_players=2)
    tournament_service.withdraw_player(tournament.id, "u1")
    tournament_service.register_player(tournament.id, "u3")

    with pytest.raises(ValueError, match="full"):
        tournament_service.register_player(tournament.id, "u1")

    assert tournament_repo.get_by_id(tournament.id).withdrawn_ids == ["u1"]


def test_register_unknown_tournament_raises(tournament_service):
    with pytest.raises(ValueError, match="no tournament"):
        tournament_service.register_player("missing", "u1")


# ---------- withdraw_player ----------

def test_withdraw_keeps_player_id_and_adds_to_withdrawn(tournament_service, tournament_repo):
    tournament = open_with_players(tournament_service, ["u1", "u2", "u3"])

    updated = tournament_service.withdraw_player(tournament.id, "u2")

    assert updated.player_ids == ["u1", "u2", "u3"]
    assert updated.withdrawn_ids == ["u2"]
    assert updated.active_player_ids == ["u1", "u3"]
    assert tournament_repo.get_by_id(tournament.id) == updated


def test_withdraw_while_draft_raises(tournament_service):
    tournament = create_round_robin(tournament_service)

    with pytest.raises(ValueError, match="cannot withdraw"):
        tournament_service.withdraw_player(tournament.id, "u1")


def test_withdraw_after_start_raises(tournament_service, tournament_repo):
    tournament = open_with_players(tournament_service, ["u1", "u2", "u3"])
    tournament_service.start_tournament(tournament.id)

    with pytest.raises(ValueError, match="cannot withdraw"):
        tournament_service.withdraw_player(tournament.id, "u3")

    assert tournament_repo.get_by_id(tournament.id).withdrawn_ids == []


def test_withdraw_unregistered_player_raises(tournament_service):
    tournament = open_with_players(tournament_service, ["u1"])

    with pytest.raises(ValueError, match="not registered"):
        tournament_service.withdraw_player(tournament.id, "u9")


def test_withdraw_twice_raises(tournament_service, tournament_repo):
    tournament = open_with_players(tournament_service, ["u1", "u2"])
    tournament_service.withdraw_player(tournament.id, "u1")

    with pytest.raises(ValueError, match="already withdrawn"):
        tournament_service.withdraw_player(tournament.id, "u1")

    assert tournament_repo.get_by_id(tournament.id).withdrawn_ids == ["u1"]


def test_withdraw_unknown_tournament_raises(tournament_service):
    with pytest.raises(ValueError, match="no tournament"):
        tournament_service.withdraw_player("missing", "u1")


# ---------- start_tournament ----------

def test_start_moves_to_in_progress_at_round_one(tournament_service, tournament_repo):
    tournament = open_with_players(tournament_service, ["u1", "u2"])

    started = tournament_service.start_tournament(tournament.id)

    assert started.status == TournamentStatus.IN_PROGRESS
    assert started.current_round == 1
    saved = tournament_repo.get_by_id(tournament.id)
    assert saved.status == TournamentStatus.IN_PROGRESS
    assert saved.current_round == 1


@pytest.mark.parametrize("player_ids", [[], ["u1"]])
def test_start_with_fewer_than_two_players_raises(tournament_service, tournament_repo, player_ids):
    tournament = open_with_players(tournament_service, player_ids)

    with pytest.raises(ValueError, match="at least 2 players"):
        tournament_service.start_tournament(tournament.id)

    assert tournament_repo.get_by_id(tournament.id).status == TournamentStatus.REGISTRATION_OPEN


def test_start_counts_only_active_players(tournament_service):
    tournament = open_with_players(tournament_service, ["u1", "u2"])
    tournament_service.withdraw_player(tournament.id, "u2")

    with pytest.raises(ValueError, match="at least 2 players"):
        tournament_service.start_tournament(tournament.id)


def test_start_while_draft_raises(tournament_service):
    tournament = create_round_robin(tournament_service)

    with pytest.raises(ValueError, match="cannot start"):
        tournament_service.start_tournament(tournament.id)


def test_start_twice_raises(tournament_service):
    tournament = open_with_players(tournament_service, ["u1", "u2"])
    tournament_service.start_tournament(tournament.id)

    with pytest.raises(ValueError, match="cannot start"):
        tournament_service.start_tournament(tournament.id)


def test_start_unknown_tournament_raises(tournament_service):
    with pytest.raises(ValueError, match="no tournament"):
        tournament_service.start_tournament("missing")


# ---------- pair_current_round ----------

def test_pair_round_one_saves_one_game_per_pair(tournament_service, game_repo):
    tournament = started_with_players(tournament_service, ["u1", "u2", "u3", "u4"])

    games = tournament_service.pair_current_round(tournament.id)

    assert len(games) == 2
    assert game_repo.list_by_tournament(tournament.id, round=1) == games
    for game in games:
        assert game.tournament_id == tournament.id
        assert game.round == 1
        assert game.result is None  # not played yet
    # Every player is in exactly one game.
    seated = [player for game in games for player in (game.white_id, game.black_id)]
    assert sorted(seated) == ["u1", "u2", "u3", "u4"]


def test_pair_uses_round_robin_pairings(tournament_service):
    tournament = started_with_players(tournament_service, ["u1", "u2", "u3", "u4"])

    games = tournament_service.pair_current_round(tournament.id)

    assert [(g.white_id, g.black_id) for g in games] == round_robin_pairings(
        ["u1", "u2", "u3", "u4"], 1
    )


def test_pair_odd_count_saves_a_bye(tournament_service, game_repo):
    tournament = started_with_players(tournament_service, ["u1", "u2", "u3"])

    games = tournament_service.pair_current_round(tournament.id)

    byes = [game for game in game_repo.list_by_tournament(tournament.id) if game.black_id is None]
    assert len(games) == 2
    assert len(byes) == 1
    assert byes[0].result == "bye"
    # Every player appears exactly once: two in the game, one with the bye.
    seated = [p for game in games for p in (game.white_id, game.black_id) if p is not None]
    assert sorted(seated) == ["u1", "u2", "u3"]


def test_pair_leaves_out_withdrawn_players(tournament_service):
    tournament = open_with_players(tournament_service, ["u1", "u2", "u3"])
    tournament_service.withdraw_player(tournament.id, "u3")
    tournament_service.start_tournament(tournament.id)

    games = tournament_service.pair_current_round(tournament.id)

    assert [(g.white_id, g.black_id) for g in games] == [("u1", "u2")]


def test_pair_gives_each_game_a_different_id(tournament_service):
    tournament = started_with_players(tournament_service, ["u1", "u2", "u3", "u4"])

    games = tournament_service.pair_current_round(tournament.id)

    assert len({game.id for game in games}) == len(games)
    assert all(len(game.id) == 32 for game in games)  # uuid4().hex


def test_pair_same_round_twice_raises(tournament_service, game_repo):
    tournament = started_with_players(tournament_service, ["u1", "u2", "u3", "u4"])
    first = tournament_service.pair_current_round(tournament.id)

    with pytest.raises(ValueError, match="already been paired"):
        tournament_service.pair_current_round(tournament.id)

    assert game_repo.list_by_tournament(tournament.id) == first


def test_pair_next_round_after_round_one(tournament_service, tournament_repo, game_repo):
    tournament = started_with_players(tournament_service, ["u1", "u2", "u3", "u4"])
    tournament_service.pair_current_round(tournament.id)
    # Moving to round 2 isn't built yet (issue #18), so set it directly.
    tournament = tournament_repo.get_by_id(tournament.id)
    tournament.current_round = 2
    tournament_repo.update(tournament)

    games = tournament_service.pair_current_round(tournament.id)

    assert {game.round for game in games} == {2}
    assert len(game_repo.list_by_tournament(tournament.id)) == 4


def test_pair_only_touches_its_own_tournament(tournament_service, game_repo):
    first = started_with_players(tournament_service, ["u1", "u2"])
    second = started_with_players(tournament_service, ["u3", "u4"])
    tournament_service.pair_current_round(first.id)

    # The other tournament's round 1 is still unpaired, so this works.
    games = tournament_service.pair_current_round(second.id)

    assert {game.tournament_id for game in games} == {second.id}
    assert len(game_repo.load_all()) == 2


@pytest.mark.parametrize("make", [create_round_robin, open_tournament])
def test_pair_before_start_raises(tournament_service, game_repo, make):
    tournament = make(tournament_service)

    with pytest.raises(ValueError, match="cannot pair round"):
        tournament_service.pair_current_round(tournament.id)

    assert game_repo.load_all() == []


def test_pair_swiss_raises(tournament_service, game_repo):
    tournament = tournament_service.create_tournament(
        name="Open", organizer_id="o1", format="swiss", max_players=4, num_rounds=3,
    )
    tournament_service.open_registration(tournament.id)
    tournament_service.register_player(tournament.id, "u1")
    tournament_service.register_player(tournament.id, "u2")
    tournament_service.start_tournament(tournament.id)

    with pytest.raises(ValueError, match="swiss pairing is not supported"):
        tournament_service.pair_current_round(tournament.id)

    assert game_repo.load_all() == []


def test_pair_unknown_tournament_raises(tournament_service):
    with pytest.raises(ValueError, match="no tournament"):
        tournament_service.pair_current_round("missing")
