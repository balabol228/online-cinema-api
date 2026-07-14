import math

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import UserGroupEnum
from app.schemas.movie import (
    MovieCreateRequest,
    MovieListItemResponse,
    MovieResponse,
    MovieUpdateRequest,
    PaginatedMoviesResponse,
)
from app.services import movie_service

router = APIRouter(prefix="/movies", tags=["Movies Catalog"])


@router.get(
    "",
    response_model=PaginatedMoviesResponse,
    summary="Перегляд каталогу фільмів (публічний)",
    description=(
        "Повертає список фільмів із пагінацією, фільтрацією та сортуванням. Доступно всім.\n\n"
        "**Параметри запиту:**\n"
        "- `page` (int, default 1), `page_size` (int, default 20, max 100)\n"
        "- `genre` — фільтр за точною назвою жанру\n"
        "- `year` — фільтр за роком випуску\n"
        "- `min_rating` — мінімальний IMDB рейтинг (0-10)\n"
        "- `search` — пошук підрядка в назві (регістронезалежний)\n"
        "- `sort_by` — одне з: `id`, `title`, `release_year`, `price`, `imdb_rating` (default `id`)\n"
        "- `sort_order` — `asc` або `desc` (default `asc`)"
    ),
)
async def get_movies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    genre: str | None = Query(default=None),
    year: int | None = Query(default=None),
    min_rating: float | None = Query(default=None, ge=0, le=10),
    search: str | None = Query(default=None),
    sort_by: str = Query(default="id"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedMoviesResponse:
    movies, total = await movie_service.list_movies(
        db,
        page=page,
        page_size=page_size,
        genre=genre,
        year=year,
        min_rating=min_rating,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PaginatedMoviesResponse(
        items=[MovieListItemResponse.model_validate(m) for m in movies],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 0,
    )


@router.get(
    "/{movie_id}",
    response_model=MovieResponse,
    summary="Деталі фільму (публічний)",
    description="Повертає повну інформацію про фільм за `movie_id`, включно з жанрами, акторами і режисером. 404, якщо не знайдено.",
)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)) -> MovieResponse:
    movie = await movie_service.get_movie_or_404(db, movie_id)
    return MovieResponse.model_validate(movie)


@router.post(
    "",
    response_model=MovieResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))],
    summary="Створити фільм (Moderator/Admin)",
    description=(
        "Створює новий фільм у каталозі. **Потребує роль Moderator або Admin** "
        "(`Authorization: Bearer <access_token>`).\n\n"
        "`genre_ids` і `actor_ids` — списки ID вже існуючих жанрів/акторів. "
        "Повертає 400, якщо якийсь із переданих ID не знайдено."
    ),
)
async def create_movie(
    payload: MovieCreateRequest, db: AsyncSession = Depends(get_db)
) -> MovieResponse:
    movie = await movie_service.create_movie(db, payload)
    return MovieResponse.model_validate(movie)


@router.patch(
    "/{movie_id}",
    response_model=MovieResponse,
    dependencies=[Depends(require_role(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))],
    summary="Оновити фільм (Moderator/Admin)",
    description=(
        "Часткове оновлення фільму — передавай лише ті поля, які хочеш змінити. "
        "**Потребує роль Moderator або Admin.** Повертає 404, якщо фільм не знайдено."
    ),
)
async def update_movie(
    movie_id: int, payload: MovieUpdateRequest, db: AsyncSession = Depends(get_db)
) -> MovieResponse:
    movie = await movie_service.update_movie(db, movie_id, payload)
    return MovieResponse.model_validate(movie)


@router.delete(
    "/{movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserGroupEnum.ADMIN))],
    summary="Видалити фільм (тільки Admin)",
    description="Видаляє фільм за `movie_id`. **Потребує роль Admin.** Повертає 404, якщо фільм не знайдено.",
)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)) -> None:
    await movie_service.delete_movie(db, movie_id)
