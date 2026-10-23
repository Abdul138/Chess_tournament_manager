from pathlib import Path

from app.config import DATA_DIR
from app.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Reads and writes users in users.json."""

    def __init__(self, file_path: Path = DATA_DIR / "users.json") -> None:
        super().__init__(file_path, User)

    def get_by_id(self, user_id: str) -> User | None:
        for user in self.load_all():
            if user.id == user_id:
                return user
        return None

    def get_by_username(self, username: str) -> User | None:
        for user in self.load_all():
            if user.username == username:
                return user
        return None

    def add(self, user: User) -> None:
        users = self.load_all()
        users.append(user)
        self.save_all(users)
