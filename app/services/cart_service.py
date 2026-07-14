from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cart import Cart, CartItem
from app.models.movie import Movie
from app.models.user import User


async def get_or_create_cart(db: AsyncSession, user: User) -> Cart:
    result = await db.scalars(
        select(Cart)
        .where(Cart.user_id == user.id)
        .options(selectinload(Cart.items).selectinload(CartItem.movie))
        .execution_options(populate_existing=True)
    )
    cart = result.first()
    if cart is None:
        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart, attribute_names=["items"])
    return cart


async def add_movie_to_cart(db: AsyncSession, user: User, movie_id: int) -> Cart:
    movie = await db.get(Movie, movie_id)
    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Фільм не знайдено")

    cart = await get_or_create_cart(db, user)

    db.add(CartItem(cart_id=cart.id, movie_id=movie_id))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Фільм вже додано в кошик"
        )

    return await get_or_create_cart(db, user)


async def remove_movie_from_cart(db: AsyncSession, user: User, movie_id: int) -> Cart:
    cart = await get_or_create_cart(db, user)

    item = next((i for i in cart.items if i.movie_id == movie_id), None)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Цього фільму немає в кошику"
        )

    await db.delete(item)
    await db.commit()
    return await get_or_create_cart(db, user)


def calculate_total_price(cart: Cart) -> float:
    return round(sum(item.movie.price for item in cart.items), 2)
