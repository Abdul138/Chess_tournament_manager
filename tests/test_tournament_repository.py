import pytest

from app.config import DATA_DIR
from app.models import Tournament, TournamentStatus
from app.repositories.tournament_repository import TournamentRepository


def make_tournament(tournament_id, name="Club Swiss"):
    return Tournament(
        id=tournament_id, name=name, organizer_id="o1",
        format="swiss", max_players=8, num_rounds=3,
    )


def test_default_path_is_data_tournaments_json():
    assert TournamentRepository().file_path == DATA_DIR / "tournaments.json"


def test_add_saves_tournament(tournament_repo):
    tournament = make_tournament("t1")

    tournament_repo.add(tournament)

    assert tournament_repo.load_all() == [tournament]


def test_add_keeps_existing_tournaments(tournament_repo):
    first = make_tournament("t1")
    second = make_tournament("t2", name="Spring Open")

    tournament_repo.add(first)
    tournament_repo.add(second)

    assert tournament_repo.load_all() == [first, second]


def test_get_by_id_finds_tournament(tournament_repo):
    tournament_repo.save_all([make_tournament("t1"), make_tournament("t2", name="Spring Open")])

    assert tournament_repo.get_by_id("t2") == make_tournament("t2", name="Spring Open")


def test_get_by_id_missing_returns_none(tournament_repo):
    tournament_repo.save_all([make_tournament("t1")])

    assert tournament_repo.get_by_id("nope") is None


def test_status_survives_round_trip(tournament_repo):
    tournament = make_tournament("t1")
    tournament.status = TournamentStatus.REGISTRATION_OPEN

    tournament_repo.add(tournament)
    loaded = tournament_repo.get_by_id("t1")

    # Saved as a plain string in the JSON file...
    assert '"registration_open"' in tournament_repo.file_path.read_text(encoding="utf-8")
    # ...and turned back into the enum (not just a string) when loaded.
    assert loaded.status is TournamentStatus.REGISTRATION_OPEN


def test_update_replaces_matching_tournament(tournament_repo):
    tournament_repo.save_all([make_tournament("t1"), make_tournament("t2", name="Spring Open")])
    changed = make_tournament("t1")
    changed.player_ids = ["u1", "u2"]

    tournament_repo.update(changed)

    # The changed tournament is saved and the other one is untouched (order kept).
    assert tournament_repo.load_all() == [changed, make_tournament("t2", name="Spring Open")]


def test_update_missing_tournament_raises(tournament_repo):
    tournament_repo.save_all([make_tournament("t1")])

    with pytest.raises(ValueError):
        tournament_repo.update(make_tournament("nope"))

    # Nothing was changed.
    assert tournament_repo.load_all() == [make_tournament("t1")]
