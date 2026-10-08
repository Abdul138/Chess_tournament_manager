from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


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
    max_players: int
    num_rounds: int
    status: TournamentStatus = TournamentStatus.DRAFT
    player_ids: list[str] = []
    withdrawn_ids: list[str] = []
    current_round: int = 0