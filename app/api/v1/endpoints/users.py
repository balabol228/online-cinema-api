from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import CurrentUserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Отримати дані поточного користувача",
    description=(
        "Повертає профіль користувача, авторизованого через `Authorization: Bearer <access_token>`.\n\n"
        "Повертає 401, якщо токен відсутній, недійсний або протермінований."
    ),
)
async def read_current_user(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(current_user)
