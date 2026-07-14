from pydantic import BaseModel

from app.models.order import OrderStatus
from app.schemas.movie import MovieListItemResponse


class OrderItemResponse(BaseModel):
    id: int
    movie: MovieListItemResponse | None
    price_at_purchase: float

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: int
    status: OrderStatus
    total_amount: float
    items: list[OrderItemResponse]

    model_config = {"from_attributes": True}


class CheckoutResponse(BaseModel):
    order: OrderResponse
    checkout_url: str
