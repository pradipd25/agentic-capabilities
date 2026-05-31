from pydantic import BaseModel


class AvatarAnimations(BaseModel):
    idle: str
    talking: str
    thinking: str
    greeting: str


class AvatarMeta(BaseModel):
    id: str
    name: str
    description: str
    thumbnail_url: str
    model_url: str
    animations: AvatarAnimations
    voice_id: str
    style: str = "3d"
