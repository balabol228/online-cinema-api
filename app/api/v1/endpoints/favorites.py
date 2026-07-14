from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.favorite import FavoriteResponse, ToggleFavoriteResponse
from app.services import favorite_service

router = APIRouter(tags=["Favorites"])


@router.post(
    "/movies/{movie_id}/favorite",
    response_model=ToggleFavoriteResponse,
    summary="Додати/прибрати фільм з обраного",
    description=(
        "Перемикає статус 'обране' для фільму: якщо фільму ще немає в обраному — додає, "
        "якщо вже є — прибирає. Повертає новий стан (`favorited`). 404, якщо фільму не існує."
    ),
)
async def toggle_favorite(
    movie_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ToggleFavoriteResponse:
    favorited = await favorite_service.toggle_favorite(db, current_user, movie_id)
    return ToggleFavoriteResponse(favorited=favorited)


@router.get(
    "/favorites",
    response_model=list[FavoriteResponse],
    summary="Список обраних фільмів ('подивитись пізніше')",
    description="Повертає список фільмів, доданих поточним користувачем в обране, найновіші спочатку.",
)
async def get_favorites(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[FavoriteResponse]:
    favorites = await favorite_service.list_favorites(db, current_user)
    return [FavoriteResponse.model_validate(f) for f in favorites]
