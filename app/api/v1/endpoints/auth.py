from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import (
    AccessTokenResponse,
    RefreshTokenRequest,
    TokenPairResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserRegisterResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Реєстрація нового користувача",
    description=(
        "Створює новий акаунт користувача.\n\n"
        "**Параметри:**\n"
        "- `email` — унікальна email-адреса\n"
        "- `password` — мінімум 8 символів, хоча б 1 цифра і 1 літера верхнього регістру\n\n"
        "**Поведінка:** новий акаунт створюється неактивним (`is_active=False`) "
        "до підтвердження email (див. `/auth/verify`, буде додано окремою фічею). "
        "Повертає 409, якщо email вже зареєстрований."
    ),
)
async def register(payload: UserRegisterRequest, db: AsyncSession = Depends(get_db)) -> UserRegisterResponse:
    user = await auth_service.register_user(db, payload.email, payload.password)
    return UserRegisterResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenPairResponse,
    summary="Логін користувача",
    description=(
        "Автентифікує користувача за email/паролем і повертає пару токенів.\n\n"
        "**Параметри:** `email`, `password`.\n\n"
        "**Повертає:** `access_token` (короткоживучий, для авторизації запитів) "
        "та `refresh_token` (довгоживучий, для оновлення access token через `/auth/refresh`)."
    ),
)
async def login(payload: UserLoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPairResponse:
    user = await auth_service.authenticate_user(db, payload.email, payload.password)
    access_token, refresh_token = await auth_service.issue_token_pair(db, user)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Оновлення access token",
    description=(
        "Видає новий `access_token` за дійсним `refresh_token`.\n\n"
        "**Параметри:** `refresh_token` — токен, отриманий під час `/auth/login`.\n\n"
        "Повертає 401, якщо токен недійсний, відкликаний або протермінований."
    ),
)
async def refresh(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)) -> AccessTokenResponse:
    access_token = await auth_service.refresh_access_token(db, payload.refresh_token)
    return AccessTokenResponse(access_token=access_token)
