from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.interaction import Comment, Like, Rating
from app.models.movie import Movie
from app.models.user import User


async def _get_movie_or_404(db: AsyncSession, movie_id: int) -> Movie:
    movie = await db.get(Movie, movie_id)
    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Фільм не знайдено")
    return movie


async def toggle_like(db: AsyncSession, user: User, movie_id: int) -> tuple[bool, int]:
    await _get_movie_or_404(db, movie_id)

    existing = await db.scalar(
        select(Like).where(Like.user_id == user.id, Like.movie_id == movie_id)
    )
    if existing:
        await db.delete(existing)
        liked = False
    else:
        db.add(Like(user_id=user.id, movie_id=movie_id))
        liked = True

    await db.commit()

    count = await db.scalar(select(func.count()).select_from(Like).where(Like.movie_id == movie_id))
    return liked, count or 0


async def rate_movie(db: AsyncSession, user: User, movie_id: int, score: int) -> None:
    await _get_movie_or_404(db, movie_id)

    existing = await db.scalar(
        select(Rating).where(Rating.user_id == user.id, Rating.movie_id == movie_id)
    )
    if existing:
        existing.score = score
    else:
        db.add(Rating(user_id=user.id, movie_id=movie_id, score=score))

    await db.commit()


async def get_rating_summary(db: AsyncSession, movie_id: int, user: User | None) -> tuple[float | None, int, int | None]:
    await _get_movie_or_404(db, movie_id)

    avg_score = await db.scalar(select(func.avg(Rating.score)).where(Rating.movie_id == movie_id))
    count = await db.scalar(select(func.count()).select_from(Rating).where(Rating.movie_id == movie_id))

    user_score = None
    if user is not None:
        user_score = await db.scalar(
            select(Rating.score).where(Rating.user_id == user.id, Rating.movie_id == movie_id)
        )

    return (round(avg_score, 2) if avg_score is not None else None), (count or 0), user_score


async def add_comment(db: AsyncSession, user: User, movie_id: int, text: str, parent_id: int | None) -> Comment:
    await _get_movie_or_404(db, movie_id)

    if parent_id is not None:
        parent = await db.get(Comment, parent_id)
        if parent is None or parent.movie_id != movie_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Батьківський коментар не знайдено"
            )

    comment = Comment(user_id=user.id, movie_id=movie_id, text=text, parent_id=parent_id)
    db.add(comment)
    await db.commit()
    await db.refresh(comment, attribute_names=["user", "replies"])
    return comment


async def list_comments(db: AsyncSession, movie_id: int) -> list[Comment]:
    await _get_movie_or_404(db, movie_id)

    result = await db.scalars(
        select(Comment)
        .where(Comment.movie_id == movie_id, Comment.parent_id.is_(None))
        .options(
            selectinload(Comment.user),
            selectinload(Comment.replies).selectinload(Comment.user),
            selectinload(Comment.replies).selectinload(Comment.replies),
        )
        .order_by(Comment.created_at.asc())
    )
    return list(result.unique().all())
