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


class TestLikes:
    async def test_like_movie(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)

        response = await client.post(f"/api/v1/movies/{movie_id}/like", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["liked"] is True
        assert body["likes_count"] == 1

    async def test_unlike_movie_toggles_off(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)

        await client.post(f"/api/v1/movies/{movie_id}/like", headers=headers)
        response = await client.post(f"/api/v1/movies/{movie_id}/like", headers=headers)
        assert response.json()["liked"] is False
        assert response.json()["likes_count"] == 0

    async def test_like_nonexistent_movie_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _create_user_and_token(db_session)
        response = await client.post("/api/v1/movies/9999/like", headers=headers)
        assert response.status_code == 404

    async def test_like_requires_auth(self, client: AsyncClient, db_session: AsyncSession) -> None:
        movie_id = await _create_movie(client, db_session)
        response = await client.post(f"/api/v1/movies/{movie_id}/like")
        assert response.status_code == 401


class TestRatings:
    async def test_rate_movie(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)

        response = await client.post(
            f"/api/v1/movies/{movie_id}/rating", json={"score": 8}, headers=headers
        )
        assert response.status_code == 200
        body = response.json()
        assert body["average_rating"] == 8.0
        assert body["user_score"] == 8

    async def test_rate_movie_updates_existing_score(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)

        await client.post(f"/api/v1/movies/{movie_id}/rating", json={"score": 5}, headers=headers)
        response = await client.post(
            f"/api/v1/movies/{movie_id}/rating", json={"score": 9}, headers=headers
        )
        body = response.json()
        assert body["ratings_count"] == 1
        assert body["average_rating"] == 9.0

    async def test_rate_movie_out_of_range_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)
        response = await client.post(
            f"/api/v1/movies/{movie_id}/rating", json={"score": 11}, headers=headers
        )
        assert response.status_code == 422

    async def test_get_rating_without_auth_is_public(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        movie_id = await _create_movie(client, db_session)
        response = await client.get(f"/api/v1/movies/{movie_id}/rating")
        assert response.status_code == 200
        assert response.json()["average_rating"] is None

    async def test_average_rating_with_multiple_users(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers1 = await _create_user_and_token(db_session, email="u1@example.com")
        headers2 = await _create_user_and_token(db_session, email="u2@example.com")
        movie_id = await _create_movie(client, db_session)

        await client.post(f"/api/v1/movies/{movie_id}/rating", json={"score": 6}, headers=headers1)
        response = await client.post(
            f"/api/v1/movies/{movie_id}/rating", json={"score": 10}, headers=headers2
        )
        assert response.json()["average_rating"] == 8.0
        assert response.json()["ratings_count"] == 2


class TestComments:
    async def test_create_top_level_comment(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)

        response = await client.post(
            f"/api/v1/movies/{movie_id}/comments", json={"text": "Great movie!"}, headers=headers
        )
        assert response.status_code == 201
        assert response.json()["text"] == "Great movie!"
        assert response.json()["parent_id"] is None

    async def test_create_nested_reply(self, client: AsyncClient, db_session: AsyncSession) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)

        parent_response = await client.post(
            f"/api/v1/movies/{movie_id}/comments", json={"text": "Parent"}, headers=headers
        )
        parent_id = parent_response.json()["id"]

        reply_response = await client.post(
            f"/api/v1/movies/{movie_id}/comments",
            json={"text": "Reply", "parent_id": parent_id},
            headers=headers,
        )
        assert reply_response.status_code == 201
        assert reply_response.json()["parent_id"] == parent_id

    async def test_reply_to_nonexistent_comment_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)
        response = await client.post(
            f"/api/v1/movies/{movie_id}/comments",
            json={"text": "Reply", "parent_id": 9999},
            headers=headers,
        )
        assert response.status_code == 404

    async def test_get_comments_includes_nested_replies(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)

        parent_response = await client.post(
            f"/api/v1/movies/{movie_id}/comments", json={"text": "Parent"}, headers=headers
        )
        parent_id = parent_response.json()["id"]
        await client.post(
            f"/api/v1/movies/{movie_id}/comments",
            json={"text": "Reply", "parent_id": parent_id},
            headers=headers,
        )

        response = await client.get(f"/api/v1/movies/{movie_id}/comments")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert len(body[0]["replies"]) == 1
        assert body[0]["replies"][0]["text"] == "Reply"

    async def test_comments_public_without_auth(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        movie_id = await _create_movie(client, db_session)
        response = await client.get(f"/api/v1/movies/{movie_id}/comments")
        assert response.status_code == 200
        assert response.json() == []
