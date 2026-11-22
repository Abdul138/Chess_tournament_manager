"""Pairing: deciding who plays whom in each round.

Only round robin is implemented so far. Swiss pairing will be added later.
"""

from collections.abc import Iterable


def round_robin_pairings(
    player_ids: list[str],
    round_number: int,
    withdrawn_ids: Iterable[str] = (),
) -> list[tuple[str, str | None]]:
    """Return the (white_id, black_id) pairs for one round of a round robin.

    - round_number starts at 1.
    - Withdrawn players are removed before pairing. Ids in withdrawn_ids that
      are not in player_ids are ignored.
    - With an odd number of players, one player gets a bye each round. A bye
      is returned as (player_id, None), matching how the Game model stores it.
    - Over all the rounds, every pair of players meets exactly once, every
      player gets exactly one bye (odd count only), and whites and blacks are
      shared out as evenly as possible.
    - Fewer than 2 players means there is nothing to pair: returns [].

    Important: the guarantees above only hold if player_ids and withdrawn_ids
    stay the same for every round. The schedule is worked out from the active
    players each time this is called, so if someone withdraws after round 1
    the later rounds are planned for a different group and pairs can repeat.
    What should happen when a player withdraws mid-tournament is not decided
    yet (see issue #7).

    Raises ValueError if a player id is repeated or round_number is out of range.

    How it works (the "circle method"): imagine the players sitting around a
    table. One seat never moves; everyone else shifts seats each round. Seat i
    plays the seat opposite it, so after enough shifts everyone has faced
    everyone. With an odd count, an empty seat (None) is added: whoever sits
    opposite it gets the bye.
    """
    withdrawn = set(withdrawn_ids)
    players = [player_id for player_id in player_ids if player_id not in withdrawn]

    if len(players) != len(set(players)):
        raise ValueError("player ids must be unique")
    if len(players) < 2:
        return []

    # ---------- Seats ----------
    # With an odd count, the empty seat goes in the seat that never moves.
    # That way every player meets the empty seat (gets the bye) exactly once.
    seats: list[str | None] = [None, *players] if len(players) % 2 == 1 else list(players)
    num_seats = len(seats)
    num_rounds = num_seats - 1  # same as Tournament.total_rounds for these players

    if not 1 <= round_number <= num_rounds:
        raise ValueError(f"round_number must be between 1 and {num_rounds}")

    # ---------- Rotate ----------
    # Seat 0 stays put; the other seats move round the table. Shifting by
    # half the table each round (instead of by one) makes colours alternate,
    # so nobody gets a long run of whites or blacks.
    fixed, moving = seats[0], seats[1:]
    shift = ((round_number - 1) * (num_seats // 2)) % len(moving)
    moving = moving[-shift:] + moving[:-shift] if shift else moving
    table = [fixed, *moving]

    # ---------- Pair up ----------
    pairs: list[tuple[str, str | None]] = []
    for board in range(num_seats // 2):
        white, black = table[board], table[num_seats - 1 - board]
        # The player in the fixed seat swaps colour every round. On every
        # other board the player in the first half of the table is white.
        if board == 0 and round_number % 2 == 0:
            white, black = black, white
        if white is None:
            # Bye: the real player goes in the white slot, black is None.
            white, black = black, white
        pairs.append((white, black))
    return pairs
