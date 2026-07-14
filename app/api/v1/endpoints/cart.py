from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.cart import AddToCartRequest, CartResponse
from app.services import cart_service

router = APIRouter(prefix="/cart", tags=["Shopping Cart"])


def _to_response(cart) -> CartResponse:
    return CartResponse(
        id=cart.id,
        items=cart.items,
        total_price=cart_service.calculate_total_price(cart),
    )


@router.get(
    "",
    response_model=CartResponse,
    summary="Переглянути кошик",
    description="Повертає вміст кошика поточного користувача разом із загальною сумою. Створює порожній кошик, якщо він ще не існує.",
)
async def get_cart(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> CartResponse:
    cart = await cart_service.get_or_create_cart(db, current_user)
    return _to_response(cart)


@router.post(
    "/items",
    response_model=CartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Додати фільм у кошик",
    description=(
        "Додає фільм (`movie_id`) у кошик поточного користувача.\n\n"
        "Повертає 404, якщо фільму не існує; 409, якщо фільм вже в кошику."
    ),
)
async def add_to_cart(
    payload: AddToCartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    cart = await cart_service.add_movie_to_cart(db, current_user, payload.movie_id)
    return _to_response(cart)


@router.delete(
    "/items/{movie_id}",
    response_model=CartResponse,
    summary="Видалити фільм із кошика",
    description="Видаляє фільм за `movie_id` із кошика поточного користувача. Повертає 404, якщо фільму немає в кошику.",
)
async def remove_from_cart(
    movie_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    cart = await cart_service.remove_movie_from_cart(db, current_user, movie_id)
    return _to_response(cart)
