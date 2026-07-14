from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.movie import Actor, Genre
from app.models.user import UserGroupEnum
from app.schemas.movie import ActorResponse, GenreResponse

router = APIRouter(tags=["Genres & Actors"])


@router.post(
    "/genres",
    response_model=GenreResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))],
    summary="Створити жанр (Moderator/Admin)",
    description="Створює новий жанр за назвою (`name`). Використовується для наповнення каталогу фільмів.",
)
async def create_genre(name: str, db: AsyncSession = Depends(get_db)) -> GenreResponse:
    genre = Genre(name=name)
    db.add(genre)
    await db.commit()
    await db.refresh(genre)
    return GenreResponse.model_validate(genre)


@router.post(
    "/actors",
    response_model=ActorResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))],
    summary="Створити актора (Moderator/Admin)",
    description="Створює нового актора за повним ім'ям (`full_name`). Використовується для наповнення каталогу фільмів.",
)
async def create_actor(full_name: str, db: AsyncSession = Depends(get_db)) -> ActorResponse:
    actor = Actor(full_name=full_name)
    db.add(actor)
    await db.commit()
    await db.refresh(actor)
    return ActorResponse.model_validate(actor)
