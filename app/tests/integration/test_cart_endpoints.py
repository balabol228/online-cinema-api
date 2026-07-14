import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserGroupEnum

pytestmark = pytest.mark.asyncio


async def _create_user_and_token(db_session: AsyncSession) -> dict[str, str]:
    user = User(email="buyer@example.com", hashed_password=hash_password("StrongPass1"), is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


async def _create_movie(client: AsyncClient, db_session: AsyncSession, title="Dune", price=12.5) -> int:
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
        json={"title": title, "release_year": 2021, "price": price, "genre_ids": [], "actor_ids": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    return response.json()["id"]


class TestCart:
    async def test_get_empty_cart(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _create_user_and_token(db_session)
        response = await client.get("/api/v1/cart", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total_price"] == 0

    async def test_add_movie_to_cart(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)

        response = await client.post(
            "/api/v1/cart/items", json={"movie_id": movie_id}, headers=headers
        )
        assert response.status_code == 201
        body = response.json()
        assert len(body["items"]) == 1
        assert body["total_price"] == 12.5

    async def test_add_nonexistent_movie_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _create_user_and_token(db_session)
        response = await client.post(
            "/api/v1/cart/items", json={"movie_id": 9999}, headers=headers
        )
        assert response.status_code == 404

    async def test_add_same_movie_twice_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)

        await client.post("/api/v1/cart/items", json={"movie_id": movie_id}, headers=headers)
        response = await client.post(
            "/api/v1/cart/items", json={"movie_id": movie_id}, headers=headers
        )
        assert response.status_code == 409

    async def test_remove_movie_from_cart(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)
        await client.post("/api/v1/cart/items", json={"movie_id": movie_id}, headers=headers)

        response = await client.delete(f"/api/v1/cart/items/{movie_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["items"] == []

    async def test_remove_movie_not_in_cart_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)
        response = await client.delete(f"/api/v1/cart/items/{movie_id}", headers=headers)
        assert response.status_code == 404

    async def test_cart_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/cart")
        assert response.status_code == 401

    async def test_total_price_with_multiple_items(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _create_user_and_token(db_session)
        movie1 = await _create_movie(client, db_session, title="Movie1", price=10.0)
        movie2 = await _create_movie(client, db_session, title="Movie2", price=5.5)

        await client.post("/api/v1/cart/items", json={"movie_id": movie1}, headers=headers)
        response = await client.post(
            "/api/v1/cart/items", json={"movie_id": movie2}, headers=headers
        )
        assert response.json()["total_price"] == 15.5
