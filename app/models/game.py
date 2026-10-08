from typing import Literal

from pydantic import BaseModel


class Game(BaseModel):
    id: str
    tournament_id: str
    round: int
    white_id: str
    black_id: str | None = None  # None means a bye
    result: Literal["1-0", "0-1", "1/2-1/2", "bye"] | None = None
    white_rating_at_start: int
    black_rating_at_start: int | None = None