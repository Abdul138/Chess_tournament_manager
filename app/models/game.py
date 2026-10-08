from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


class Game(BaseModel):
    id: str
    tournament_id: str
    round: int = Field(ge=1)
    white_id: str
    black_id: str | None = None  # None means a bye
    result: Literal["1-0", "0-1", "1/2-1/2", "bye"] | None = None  # None means not played yet

    @model_validator(mode="after")
    def check_players(self) -> Self:
        if self.white_id == self.black_id:
            raise ValueError("a player cannot play themselves")
        if (self.black_id is None) != (self.result == "bye"):
            raise ValueError('a bye must have no black player and result "bye"')
        return self