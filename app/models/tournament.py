from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


class TournamentStatus(StrEnum):
    DRAFT = "draft"
    REGISTRATION_OPEN = "registration_open"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class Tournament(BaseModel):
    id: str
    name: str
    organizer_id: str
    format: Literal["round_robin", "swiss"]
    max_players: int = Field(ge=2)
    num_rounds: int | None = Field(default=None, ge=1)  # Swiss only; round robin calculates it
    status: TournamentStatus = TournamentStatus.DRAFT
    player_ids: list[str] = []
    withdrawn_ids: list[str] = []
    current_round: int = 0

    @model_validator(mode="after")
    def check_num_rounds(self) -> Self:
        if self.format == "swiss" and self.num_rounds is None:
            raise ValueError("swiss tournaments must set num_rounds")
        if self.format == "round_robin" and self.num_rounds is not None:
            raise ValueError("round robin calculates its rounds; do not set num_rounds")
        return self

    @property
    def active_player_ids(self) -> list[str]:
        """Registered players who have not withdrawn, in registration order."""
        withdrawn = set(self.withdrawn_ids)
        return [player_id for player_id in self.player_ids if player_id not in withdrawn]

    @property
    def total_rounds(self) -> int:
        if self.format == "swiss":
            return self.num_rounds
        # Only active players count. The rule (issue #7) is that players may
        # only withdraw before round 1, so players who withdrew never play.
        # TournamentService.withdraw_player enforces that rule.
        n = len(self.active_player_ids)
        if n < 2:
            return 0
        # With an odd count, one player sits out (bye) each round, so it takes n rounds.
        return n - 1 if n % 2 == 0 else n