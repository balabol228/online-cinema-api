from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserGroupEnum

pytestmark = pytest.mark.asyncio


async def _create_user_and_token(db_session: AsyncSession, email="buyer@example.com") -> dict:
    user = User(email=email, hashed_password=hash_password("StrongPass1"), is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


async def _create_movie(client: AsyncClient, db_session: AsyncSession, title="Dune", price=10.0) -> int:
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


FAKE_CHECKOUT_URL = "https://checkout.stripe.com/pay/cs_test_fake123"


class TestCheckout:
    @patch("app.services.order_service.payment_service.create_checkout_session", return_value=FAKE_CHECKOUT_URL)
    async def test_checkout_creates_order_and_returns_url(
        self, mock_stripe, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)
        await client.post("/api/v1/cart/items", json={"movie_id": movie_id}, headers=headers)

        response = await client.post("/api/v1/orders", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["checkout_url"] == FAKE_CHECKOUT_URL
        assert body["order"]["status"] == "pending"
        assert body["order"]["total_amount"] == 10.0
        mock_stripe.assert_called_once()

    async def test_checkout_with_empty_cart_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _create_user_and_token(db_session)
        response = await client.post("/api/v1/orders", headers=headers)
        assert response.status_code == 400

    @patch("app.services.order_service.payment_service.create_checkout_session", return_value=FAKE_CHECKOUT_URL)
    async def test_checkout_empties_cart(
        self, mock_stripe, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)
        await client.post("/api/v1/cart/items", json={"movie_id": movie_id}, headers=headers)

        await client.post("/api/v1/orders", headers=headers)
        cart_response = await client.get("/api/v1/cart", headers=headers)
        assert cart_response.json()["items"] == []

    async def test_checkout_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/orders")
        assert response.status_code == 401


class TestOrderHistory:
    @patch("app.services.order_service.payment_service.create_checkout_session", return_value=FAKE_CHECKOUT_URL)
    async def test_list_orders(
        self, mock_stripe, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)
        await client.post("/api/v1/cart/items", json={"movie_id": movie_id}, headers=headers)
        await client.post("/api/v1/orders", headers=headers)

        response = await client.get("/api/v1/orders", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_get_order_not_found_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _create_user_and_token(db_session)
        response = await client.get("/api/v1/orders/9999", headers=headers)
        assert response.status_code == 404

    @patch("app.services.order_service.payment_service.create_checkout_session", return_value=FAKE_CHECKOUT_URL)
    async def test_user_cannot_see_other_users_order(
        self, mock_stripe, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers1 = await _create_user_and_token(db_session, email="user1@example.com")
        headers2 = await _create_user_and_token(db_session, email="user2@example.com")
        movie_id = await _create_movie(client, db_session)
        await client.post("/api/v1/cart/items", json={"movie_id": movie_id}, headers=headers1)
        order_response = await client.post("/api/v1/orders", headers=headers1)
        order_id = order_response.json()["order"]["id"]

        response = await client.get(f"/api/v1/orders/{order_id}", headers=headers2)
        assert response.status_code == 404


class TestWebhook:
    @patch("app.services.order_service.payment_service.create_checkout_session", return_value=FAKE_CHECKOUT_URL)
    @patch("app.api.v1.endpoints.payments.payment_service.verify_webhook_event")
    async def test_webhook_marks_order_as_paid(
        self,
        mock_verify,
        mock_checkout,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        headers = await _create_user_and_token(db_session)
        movie_id = await _create_movie(client, db_session)
        await client.post("/api/v1/cart/items", json={"movie_id": movie_id}, headers=headers)
        order_response = await client.post("/api/v1/orders", headers=headers)
        order_id = order_response.json()["order"]["id"]

        session_id = FAKE_CHECKOUT_URL.split("/")[-1]
        mock_verify.return_value = {
            "type": "checkout.session.completed",
            "data": {"object": {"id": session_id}},
        }

        webhook_response = await client.post(
            "/api/v1/payments/webhook",
            content=b"{}",
            headers={"stripe-signature": "fake-sig"},
        )
        assert webhook_response.status_code == 200

        order_check = await client.get(f"/api/v1/orders/{order_id}", headers=headers)
        assert order_check.json()["status"] == "paid"

    @patch("app.api.v1.endpoints.payments.payment_service.verify_webhook_event", side_effect=Exception("bad sig"))
    async def test_webhook_invalid_signature_returns_400(
        self, mock_verify, client: AsyncClient
    ) -> None:
        response = await client.post(
            "/api/v1/payments/webhook",
            content=b"{}",
            headers={"stripe-signature": "invalid"},
        )
        assert response.status_code == 400
