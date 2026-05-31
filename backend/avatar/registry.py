import json
from pathlib import Path

from backend.avatar.models import AvatarMeta


class AvatarRegistry:
    def __init__(self, manifest_path: Path):
        self._avatars: dict[str, AvatarMeta] = {}
        self._load(manifest_path)

    def _load(self, path: Path) -> None:
        with open(path) as f:
            data = json.load(f)
        for entry in data["avatars"]:
            meta = AvatarMeta(**entry)
            self._avatars[meta.id] = meta

    def list_avatars(self) -> list[AvatarMeta]:
        return list(self._avatars.values())

    def get_avatar(self, avatar_id: str) -> AvatarMeta | None:
        return self._avatars.get(avatar_id)
