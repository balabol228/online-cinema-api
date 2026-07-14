from pydantic import BaseModel

from app.schemas.movie import MovieListItemResponse


class AddToCartRequest(BaseModel):
    movie_id: int


class CartItemResponse(BaseModel):
    id: int
    movie: MovieListItemResponse

    model_config = {"from_attributes": True}


class CartResponse(BaseModel):
    id: int
    items: list[CartItemResponse]
    total_price: float

    model_config = {"from_attributes": True}
