from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User
from app.services import cart_service, payment_service

ORDER_LOAD_OPTIONS = (selectinload(Order.items).selectinload(OrderItem.movie),)


async def create_order_from_cart(db: AsyncSession, user: User) -> tuple[Order, str]:
    cart = await cart_service.get_or_create_cart(db, user)
    if not cart.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Кошик порожній")

    total = cart_service.calculate_total_price(cart)
    order = Order(user_id=user.id, total_amount=total, status=OrderStatus.PENDING)
    order.items = [
        OrderItem(movie_id=item.movie_id, price_at_purchase=item.movie.price) for item in cart.items
    ]
    db.add(order)

    for item in list(cart.items):
        await db.delete(item)

    await db.commit()
    await db.refresh(order, attribute_names=["items"])
    for item in order.items:
        await db.refresh(item, attribute_names=["movie"])

    checkout_url = payment_service.create_checkout_session(order)
    order.stripe_checkout_session_id = checkout_url.split("/")[-1] if checkout_url else None
    await db.commit()
    await db.refresh(order, attribute_names=["items"])

    return order, checkout_url


async def list_orders(db: AsyncSession, user: User) -> list[Order]:
    result = await db.scalars(
        select(Order)
        .where(Order.user_id == user.id)
        .options(*ORDER_LOAD_OPTIONS)
        .order_by(Order.created_at.desc())
    )
    return list(result.unique().all())


async def get_order_or_404(db: AsyncSession, user: User, order_id: int) -> Order:
    result = await db.scalars(
        select(Order)
        .where(Order.id == order_id, Order.user_id == user.id)
        .options(*ORDER_LOAD_OPTIONS)
    )
    order = result.first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Замовлення не знайдено")
    return order


async def mark_order_paid_by_session_id(db: AsyncSession, checkout_session_id: str) -> None:
    result = await db.scalars(
        select(Order).where(Order.stripe_checkout_session_id == checkout_session_id)
    )
    order = result.first()
    if order is not None:
        order.status = OrderStatus.PAID
        await db.commit()
