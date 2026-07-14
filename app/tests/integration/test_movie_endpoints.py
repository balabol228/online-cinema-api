import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserGroupEnum

pytestmark = pytest.mark.asyncio


async def _create_user(db_session: AsyncSession, group: UserGroupEnum) -> User:
    user = User(
        email=f"{group.value}@example.com",
        hashed_password=hash_password("StrongPass1"),
        is_active=True,
        group=group,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _auth_headers(db_session: AsyncSession, group: UserGroupEnum) -> dict[str, str]:
    user = await _create_user(db_session, group)
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


async def _create_movie(client: AsyncClient, headers: dict[str, str], **overrides) -> dict:
    payload = {
        "title": "Inception",
        "description": "A mind-bending heist",
        "release_year": 2010,
        "price": 9.99,
        "imdb_rating": 8.8,
        "genre_ids": [],
        "actor_ids": [],
    }
    payload.update(overrides)
    response = await client.post("/api/v1/movies", json=payload, headers=headers)
    return response


class TestCreateMovie:
    async def test_admin_can_create_movie(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _auth_headers(db_session, UserGroupEnum.ADMIN)
        response = await _create_movie(client, headers)
        assert response.status_code == 201
        assert response.json()["title"] == "Inception"

    async def test_moderator_can_create_movie(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _auth_headers(db_session, UserGroupEnum.MODERATOR)
        response = await _create_movie(client, headers)
        assert response.status_code == 201

    async def test_regular_user_cannot_create_movie(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _auth_headers(db_session, UserGroupEnum.USER)
        response = await _create_movie(client, headers)
        assert response.status_code == 403

    async def test_create_movie_without_auth_returns_401(self, client: AsyncClient) -> None:
        response = await _create_movie(client, headers={})
        assert response.status_code == 401

    async def test_create_movie_with_invalid_genre_id_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _auth_headers(db_session, UserGroupEnum.ADMIN)
        response = await _create_movie(client, headers, genre_ids=[999])
        assert response.status_code == 400


class TestGetMovies:
    async def test_get_movie_list_public(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _auth_headers(db_session, UserGroupEnum.ADMIN)
        await _create_movie(client, headers)
        await _create_movie(client, headers, title="The Matrix", release_year=1999)

        response = await client.get("/api/v1/movies")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2

    async def test_get_movie_detail_not_found_returns_404(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/movies/9999")
        assert response.status_code == 404

    async def test_filter_by_year(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _auth_headers(db_session, UserGroupEnum.ADMIN)
        await _create_movie(client, headers, title="Old Movie", release_year=1995)
        await _create_movie(client, headers, title="New Movie", release_year=2020)

        response = await client.get("/api/v1/movies", params={"year": 2020})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["title"] == "New Movie"

    async def test_search_by_title(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _auth_headers(db_session, UserGroupEnum.ADMIN)
        await _create_movie(client, headers, title="Interstellar")
        await _create_movie(client, headers, title="The Matrix")

        response = await client.get("/api/v1/movies", params={"search": "inter"})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["title"] == "Interstellar"

    async def test_pagination(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _auth_headers(db_session, UserGroupEnum.ADMIN)
        for i in range(5):
            await _create_movie(client, headers, title=f"Movie {i}")

        response = await client.get("/api/v1/movies", params={"page": 1, "page_size": 2})
        body = response.json()
        assert len(body["items"]) == 2
        assert body["total"] == 5
        assert body["total_pages"] == 3

    async def test_sort_by_price_desc(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _auth_headers(db_session, UserGroupEnum.ADMIN)
        await _create_movie(client, headers, title="Cheap", price=1.0)
        await _create_movie(client, headers, title="Expensive", price=99.0)

        response = await client.get(
            "/api/v1/movies", params={"sort_by": "price", "sort_order": "desc"}
        )
        body = response.json()
        assert body["items"][0]["title"] == "Expensive"


class TestUpdateDeleteMovie:
    async def test_admin_can_update_movie(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _auth_headers(db_session, UserGroupEnum.ADMIN)
        create_response = await _create_movie(client, headers)
        movie_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/movies/{movie_id}", json={"price": 15.5}, headers=headers
        )
        assert response.status_code == 200
        assert response.json()["price"] == 15.5

    async def test_only_admin_can_delete_movie(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        admin_headers = await _auth_headers(db_session, UserGroupEnum.ADMIN)
        moderator_headers = await _auth_headers(db_session, UserGroupEnum.MODERATOR)
        create_response = await _create_movie(client, admin_headers)
        movie_id = create_response.json()["id"]

        forbidden_response = await client.delete(
            f"/api/v1/movies/{movie_id}", headers=moderator_headers
        )
        assert forbidden_response.status_code == 403

        response = await client.delete(f"/api/v1/movies/{movie_id}", headers=admin_headers)
        assert response.status_code == 204

        get_response = await client.get(f"/api/v1/movies/{movie_id}")
        assert get_response.status_code == 404
