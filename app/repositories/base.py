import json
from pathlib import Path

from pydantic import BaseModel


class BaseRepository[T: BaseModel]:
    """Stores a list of Pydantic models in one JSON file.

    T stands for whichever model this repository holds (User, Tournament, Game).
    """

    def __init__(self, file_path: Path, model: type[T]) -> None:
        self.file_path = file_path
        self.model = model

    def load_all(self) -> list[T]:
        """Read the JSON file and turn each entry into a validated model.

        If the file doesn't exist yet, create it as an empty list.
        """
        try:
            text = self.file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self.file_path.write_text("[]", encoding="utf-8")
            return []
        data = json.loads(text)
        return [self.model.model_validate(item) for item in data]

    def save_all(self, items: list[T]) -> None:
        """Replace the file's contents with the given models."""
        # mode="json" converts values like enums into plain JSON types.
        data = [item.model_dump(mode="json") for item in items]
        self.file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
