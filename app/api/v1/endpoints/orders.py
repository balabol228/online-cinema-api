from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.order import CheckoutResponse, OrderResponse
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["Orders & Payment"])


@router.post(
    "",
    response_model=CheckoutResponse,
    summary="Оформити замовлення з кошика",
    description=(
        "Створює замовлення з усіх фільмів у кошику поточного користувача, "
        "очищує кошик і повертає посилання на сторінку оплати Stripe Checkout.\n\n"
        "Повертає 400, якщо кошик порожній. Статус замовлення одразу після створення — `pending`, "
        "змінюється на `paid` після підтвердження оплати через `/orders/webhook` (Stripe webhook)."
    ),
)
async def checkout(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> CheckoutResponse:
    order, checkout_url = await order_service.create_order_from_cart(db, current_user)
    return CheckoutResponse(order=OrderResponse.model_validate(order), checkout_url=checkout_url)


@router.get(
    "",
    response_model=list[OrderResponse],
    summary="Історія замовлень",
    description="Повертає всі замовлення поточного користувача, найновіші спочатку.",
)
async def get_orders(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[OrderResponse]:
    orders = await order_service.list_orders(db, current_user)
    return [OrderResponse.model_validate(o) for o in orders]


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Деталі замовлення",
    description="Повертає деталі одного замовлення поточного користувача. 404, якщо не знайдено або належить іншому користувачу.",
)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    order = await order_service.get_order_or_404(db, current_user, order_id)
    return OrderResponse.model_validate(order)
