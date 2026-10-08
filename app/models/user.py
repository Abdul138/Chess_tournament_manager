from typing import Literal

from pydantic import BaseModel, Field


class User(BaseModel):
    id: str
    username: str
    password_hash: str
    role: Literal["player", "organizer"]
    rating: int = Field(default=1000, ge=0)  # ge=0: negative ratings are rejected