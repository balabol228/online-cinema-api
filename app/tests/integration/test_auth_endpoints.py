import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

pytestmark = pytest.mark.asyncio


async def _register(client: AsyncClient, email: str = "user@example.com", password: str = "StrongPass1"):
    return await client.post("/api/v1/auth/register", json={"email": email, "password": password})


class TestRegister:
    async def test_register_creates_inactive_user(self, client: AsyncClient, db_session: AsyncSession) -> None:
        response = await _register(client)
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "user@example.com"
        assert body["is_active"] is False

        user = await db_session.scalar(select(User).where(User.email == "user@example.com"))
        assert user is not None

    async def test_register_duplicate_email_returns_409(self, client: AsyncClient) -> None:
        await _register(client)
        response = await _register(client)
        assert response.status_code == 409

    async def test_register_weak_password_returns_422(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/auth/register", json={"email": "u2@example.com", "password": "weak"})
        assert response.status_code == 422


class TestLogin:
    async def test_login_inactive_user_returns_403(self, client: AsyncClient) -> None:
        await _register(client)
        response = await client.post(
            "/api/v1/auth/login", json={"email": "user@example.com", "password": "StrongPass1"}
        )
        assert response.status_code == 403

    async def test_login_success_returns_token_pair(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await _register(client)
        user = await db_session.scalar(select(User).where(User.email == "user@example.com"))
        user.is_active = True
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login", json={"email": "user@example.com", "password": "StrongPass1"}
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body

    async def test_login_wrong_password_returns_401(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await _register(client)
        user = await db_session.scalar(select(User).where(User.email == "user@example.com"))
        user.is_active = True
        await db_session.commit()

        response = await client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "WrongPass1"})
        assert response.status_code == 401


class TestRefreshToken:
    async def test_refresh_returns_new_access_token(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await _register(client)
        user = await db_session.scalar(select(User).where(User.email == "user@example.com"))
        user.is_active = True
        await db_session.commit()

        login_response = await client.post(
            "/api/v1/auth/login", json={"email": "user@example.com", "password": "StrongPass1"}
        )
        refresh_token = login_response.json()["refresh_token"]

        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_refresh_with_invalid_token_returns_401(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid-token"})
        assert response.status_code == 401
