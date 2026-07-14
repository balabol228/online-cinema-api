import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserGroupEnum

pytestmark = pytest.mark.asyncio


async def _create_user_and_token(db_session: AsyncSession, email="user@example.com") -> dict:
    user = User(email=email, hashed_password=hash_password("StrongPass1"), is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


async def _create_movie(client: AsyncClient, db_session: AsyncSession, title="Dune") -> int:
    admin = User(
        email=f"admin_{title}@example.com",
        hashed_password=hash_password("StrongPass1"),
        is_active=True,
        group=UserGroupEnum.ADMIN,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    admin_token = create_access_token(admin.id)
    response = await client.post(
        "/api/v1/movies",
        json={"title": title, "release_year": 2021, "price": 9.99, "genre_ids": [], "actor_ids": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    return response.json()["id"]


class TestFavorites:
    async def test_add_to_favorites(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)

        response = await client.post(f"/api/v1/movies/{movie_id}/favorite", headers=headers)
        assert response.status_code == 200
        assert response.json()["favorited"] is True

    async def test_toggle_removes_from_favorites(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)

        await client.post(f"/api/v1/movies/{movie_id}/favorite", headers=headers)
        response = await client.post(f"/api/v1/movies/{movie_id}/favorite", headers=headers)
        assert response.json()["favorited"] is False

    async def test_favorite_nonexistent_movie_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _create_user_and_token(db_session)
        response = await client.post("/api/v1/movies/9999/favorite", headers=headers)
        assert response.status_code == 404

    async def test_favorite_requires_auth(self, client: AsyncClient, db_session: AsyncSession) -> None:
        movie_id = await _create_movie(client, db_session)
        response = await client.post(f"/api/v1/movies/{movie_id}/favorite")
        assert response.status_code == 401

    async def test_list_favorites(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _create_user_and_token(db_session)
        movie1 = await _create_movie(client, db_session, title="Movie1")
        movie2 = await _create_movie(client, db_session, title="Movie2")

        await client.post(f"/api/v1/movies/{movie1}/favorite", headers=headers)
        await client.post(f"/api/v1/movies/{movie2}/favorite", headers=headers)

        response = await client.get("/api/v1/favorites", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    async def test_favorites_isolated_per_user(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers1 = await _create_user_and_token(db_session, email="u1@example.com")
        headers2 = await _create_user_and_token(db_session, email="u2@example.com")
        movie_id = await _create_movie(client, db_session)

        await client.post(f"/api/v1/movies/{movie_id}/favorite", headers=headers1)

        response = await client.get("/api/v1/favorites", headers=headers2)
        assert response.json() == []
