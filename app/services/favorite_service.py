from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.favorite import Favorite
from app.models.movie import Movie
from app.models.user import User


async def toggle_favorite(db: AsyncSession, user: User, movie_id: int) -> bool:
    movie = await db.get(Movie, movie_id)
    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Фільм не знайдено")

    existing = await db.scalar(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.movie_id == movie_id)
    )
    if existing:
        await db.delete(existing)
        await db.commit()
        return False

    db.add(Favorite(user_id=user.id, movie_id=movie_id))
    await db.commit()
    return True


async def list_favorites(db: AsyncSession, user: User) -> list[Favorite]:
    result = await db.scalars(
        select(Favorite)
        .where(Favorite.user_id == user.id)
        .options(selectinload(Favorite.movie))
        .order_by(Favorite.added_at.desc())
    )
    return list(result.all())
