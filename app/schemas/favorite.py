from pydantic import BaseModel

from app.schemas.movie import MovieListItemResponse


class FavoriteResponse(BaseModel):
    id: int
    movie: MovieListItemResponse

    model_config = {"from_attributes": True}


class ToggleFavoriteResponse(BaseModel):
    favorited: bool
