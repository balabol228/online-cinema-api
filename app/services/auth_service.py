from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import RefreshToken, User


async def register_user(db: AsyncSession, email: str, password: str) -> User:
    """
    Реєструє нового користувача.
    Кидає 409, якщо email вже зайнятий.
    Примітка: у продакшн-версії тут також надсилається email для верифікації акаунту.
    """
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Користувач з таким email вже існує",
        )

    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """Перевіряє email/пароль. Кидає 401 при невдачі."""
    user = await db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірний email або пароль",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Акаунт неактивний. Підтвердіть email.",
        )
    return user


async def issue_token_pair(db: AsyncSession, user: User) -> tuple[str, str]:
    """Створює пару access + refresh токенів і зберігає refresh token у БД."""
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    db.add(
        RefreshToken(
            token=refresh_token,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    await db.commit()
    return access_token, refresh_token


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> str:
    """
    Видає новий access token за дійсним refresh token.
    Перевіряє: валідність підпису, тип токена, наявність у БД, термін дії.
    """
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недійсний refresh token")

    stored = await db.scalar(select(RefreshToken).where(RefreshToken.token == refresh_token))
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token не знайдено (можливо, вже відкликаний)",
        )

    expires_at = stored.expires_at
    if expires_at.tzinfo is None:
        # SQLite (у тестах) не зберігає timezone-інформацію на відміну від Postgres
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Термін дії refresh token сплив")

    return create_access_token(int(payload["sub"]))
