from typing import Literal

from pydantic import BaseModel


class User(BaseModel):
    id: str
    username: str
    password_hash: str
    role: Literal["player", "organizer", "admin"]
    rating: int = 1200
    active: bool = True