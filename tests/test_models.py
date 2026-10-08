import pytest
from pydantic import ValidationError

from app.models import Game, Tournament, TournamentStatus, User


# ---------- User ----------

def test_create_valid_user():
    user = User(id="u1", username="magnus", password_hash="hashed", role="player")

    assert user.username == "magnus"
    assert user.role == "player"
    assert user.rating == 1000  # default starting rating


def test_organizer_role_is_allowed():
    user = User(id="u2", username="org", password_hash="hashed", role="organizer")

    assert user.role == "organizer"


@pytest.mark.parametrize("role", ["superuser", "admin"])
def test_invalid_role_raises(role):
    with pytest.raises(ValidationError):
        User(id="u1", username="magnus", password_hash="hashed", role=role)


def test_negative_rating_raises():
    with pytest.raises(ValidationError):
        User(id="u1", username="magnus", password_hash="hashed", role="player", rating=-1)


def test_zero_rating_is_allowed():
    user = User(id="u1", username="magnus", password_hash="hashed", role="player", rating=0)

    assert user.rating == 0


# ---------- Game ----------

def test_create_valid_game():
    game = Game(id="g1", tournament_id="t1", round=1, white_id="u1", black_id="u2")

    assert game.result is None  # not played yet


def test_game_with_result():
    game = Game(id="g1", tournament_id="t1", round=1, white_id="u1", black_id="u2", result="1/2-1/2")

    assert game.result == "1/2-1/2"


def test_create_bye():
    game = Game(id="g1", tournament_id="t1", round=1, white_id="u1", black_id=None, result="bye")

    assert game.black_id is None


def test_player_cannot_play_themselves():
    with pytest.raises(ValidationError):
        Game(id="g1", tournament_id="t1", round=1, white_id="u1", black_id="u1")


def test_invalid_result_raises():
    with pytest.raises(ValidationError):
        Game(id="g1", tournament_id="t1", round=1, white_id="u1", black_id="u2", result="2-0")


def test_bye_result_requires_no_black_player():
    with pytest.raises(ValidationError):
        Game(id="g1", tournament_id="t1", round=1, white_id="u1", black_id="u2", result="bye")


def test_missing_black_player_requires_bye_result():
    with pytest.raises(ValidationError):
        Game(id="g1", tournament_id="t1", round=1, white_id="u1", black_id=None)


def test_round_zero_raises():
    with pytest.raises(ValidationError):
        Game(id="g1", tournament_id="t1", round=0, white_id="u1", black_id="u2")


# ---------- Tournament ----------

def make_round_robin(player_ids=()):
    return Tournament(
        id="t1", name="Club RR", organizer_id="o1", format="round_robin",
        max_players=8, player_ids=list(player_ids),
    )


def test_create_valid_swiss():
    t = Tournament(id="t1", name="Open", organizer_id="o1", format="swiss", max_players=16, num_rounds=5)

    assert t.status == TournamentStatus.DRAFT  # new tournaments start as drafts
    assert t.player_ids == []
    assert t.current_round == 0
    assert t.total_rounds == 5


def test_swiss_requires_num_rounds():
    with pytest.raises(ValidationError):
        Tournament(id="t1", name="Open", organizer_id="o1", format="swiss", max_players=16)


def test_round_robin_rejects_num_rounds():
    with pytest.raises(ValidationError):
        Tournament(
            id="t1", name="Club RR", organizer_id="o1", format="round_robin",
            max_players=8, num_rounds=3,
        )


@pytest.mark.parametrize(
    ("num_players", "expected_rounds"),
    [(0, 0), (1, 0), (2, 1), (4, 3), (5, 5), (6, 5)],
)
def test_round_robin_total_rounds(num_players, expected_rounds):
    t = make_round_robin(player_ids=[f"u{i}" for i in range(num_players)])

    assert t.total_rounds == expected_rounds


def test_invalid_format_raises():
    with pytest.raises(ValidationError):
        Tournament(id="t1", name="X", organizer_id="o1", format="knockout", max_players=8, num_rounds=3)


def test_max_players_below_two_raises():
    with pytest.raises(ValidationError):
        Tournament(id="t1", name="X", organizer_id="o1", format="swiss", max_players=1, num_rounds=3)


def test_num_rounds_zero_raises():
    with pytest.raises(ValidationError):
        Tournament(id="t1", name="X", organizer_id="o1", format="swiss", max_players=8, num_rounds=0)


def test_invalid_status_raises():
    with pytest.raises(ValidationError):
        Tournament(
            id="t1", name="X", organizer_id="o1", format="swiss",
            max_players=8, num_rounds=3, status="paused",
        )
