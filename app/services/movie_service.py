from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.movie import Actor, Genre, Movie
from app.schemas.movie import MovieCreateRequest, MovieUpdateRequest

MOVIE_LOAD_OPTIONS = (selectinload(Movie.director), selectinload(Movie.genres), selectinload(Movie.actors))


async def _resolve_genres(db: AsyncSession, genre_ids: list[int]) -> list[Genre]:
    if not genre_ids:
        return []
    result = await db.scalars(select(Genre).where(Genre.id.in_(genre_ids)))
    genres = list(result.all())
    missing = set(genre_ids) - {g.id for g in genres}
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Жанри не знайдено: {sorted(missing)}"
        )
    return genres


async def _resolve_actors(db: AsyncSession, actor_ids: list[int]) -> list[Actor]:
    if not actor_ids:
        return []
    result = await db.scalars(select(Actor).where(Actor.id.in_(actor_ids)))
    actors = list(result.all())
    missing = set(actor_ids) - {a.id for a in actors}
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Акторів не знайдено: {sorted(missing)}"
        )
    return actors


async def create_movie(db: AsyncSession, payload: MovieCreateRequest) -> Movie:
    """Створює новий фільм. Доступно лише Moderator/Admin (перевіряється на рівні ендпоінту)."""
    genres = await _resolve_genres(db, payload.genre_ids)
    actors = await _resolve_actors(db, payload.actor_ids)

    movie = Movie(
        title=payload.title,
        description=payload.description,
        release_year=payload.release_year,
        price=payload.price,
        imdb_rating=payload.imdb_rating,
        director_id=payload.director_id,
        genres=genres,
        actors=actors,
    )
    db.add(movie)
    await db.commit()
    await db.refresh(movie, attribute_names=["director", "genres", "actors"])
    return movie


async def get_movie_or_404(db: AsyncSession, movie_id: int) -> Movie:
    result = await db.scalars(
        select(Movie).where(Movie.id == movie_id).options(*MOVIE_LOAD_OPTIONS)
    )
    movie = result.first()
    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Фільм не знайдено")
    return movie


async def update_movie(db: AsyncSession, movie_id: int, payload: MovieUpdateRequest) -> Movie:
    movie = await get_movie_or_404(db, movie_id)

    data = payload.model_dump(exclude_unset=True, exclude={"genre_ids", "actor_ids"})
    for field, value in data.items():
        setattr(movie, field, value)

    if payload.genre_ids is not None:
        movie.genres = await _resolve_genres(db, payload.genre_ids)
    if payload.actor_ids is not None:
        movie.actors = await _resolve_actors(db, payload.actor_ids)

    await db.commit()
    await db.refresh(movie, attribute_names=["director", "genres", "actors"])
    return movie


async def delete_movie(db: AsyncSession, movie_id: int) -> None:
    movie = await get_movie_or_404(db, movie_id)
    await db.delete(movie)
    await db.commit()


async def list_movies(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    genre: str | None = None,
    year: int | None = None,
    min_rating: float | None = None,
    search: str | None = None,
    sort_by: str = "id",
    sort_order: str = "asc",
) -> tuple[list[Movie], int]:
    query = select(Movie).options(*MOVIE_LOAD_OPTIONS)
    count_query = select(func.count(func.distinct(Movie.id)))

    if genre:
        query = query.join(Movie.genres).where(Genre.name.ilike(genre))
        count_query = count_query.join(Movie.genres).where(Genre.name.ilike(genre))
    if year is not None:
        query = query.where(Movie.release_year == year)
        count_query = count_query.where(Movie.release_year == year)
    if min_rating is not None:
        query = query.where(Movie.imdb_rating >= min_rating)
        count_query = count_query.where(Movie.imdb_rating >= min_rating)
    if search:
        query = query.where(Movie.title.ilike(f"%{search}%"))
        count_query = count_query.where(Movie.title.ilike(f"%{search}%"))

    sort_columns = {
        "id": Movie.id,
        "title": Movie.title,
        "release_year": Movie.release_year,
        "price": Movie.price,
        "imdb_rating": Movie.imdb_rating,
    }
    sort_column = sort_columns.get(sort_by, Movie.id)
    query = query.order_by(sort_column.desc() if sort_order == "desc" else sort_column.asc())

    total = (await db.execute(count_query)).scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size)
    movies = list((await db.scalars(query)).unique().all())

    return movies, total
