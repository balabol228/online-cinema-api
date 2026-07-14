import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token
from app.models.user import User, UserGroupEnum

pytestmark = pytest.mark.asyncio


async def _create_active_user(
    db_session: AsyncSession, email: str = "user@example.com", group: UserGroupEnum = UserGroupEnum.USER
) -> User:
    from app.core.security import hash_password

    user = User(email=email, hashed_password=hash_password("StrongPass1"), is_active=True, group=group)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestGetCurrentUser:
    async def test_me_without_token_returns_401(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_me_with_invalid_token_returns_401(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/users/me", headers={"Authorization": "Bearer not-a-real-token"}
        )
        assert response.status_code == 401

    async def test_me_with_refresh_token_instead_of_access_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_active_user(db_session)
        refresh_token = create_refresh_token(user.id)
        response = await client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {refresh_token}"}
        )
        assert response.status_code == 401

    async def test_me_with_valid_token_returns_user_data(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _create_active_user(db_session)
        access_token = create_access_token(user.id)
        response = await client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == "user@example.com"
        assert body["group"] == "user"

    async def test_me_for_deleted_user_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        access_token = create_access_token(user_id=999999)
        response = await client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 401
