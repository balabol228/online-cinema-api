import stripe

from app.core.config import settings
from app.models.order import Order

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_checkout_session(order: Order) -> str:
    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": item.movie.title if item.movie else "Movie"},
                    "unit_amount": int(item.price_at_purchase * 100),
                },
                "quantity": 1,
            }
            for item in order.items
        ],
        success_url="https://online-cinema.example.com/orders/success",
        cancel_url="https://online-cinema.example.com/orders/cancel",
        metadata={"order_id": str(order.id)},
    )
    return session.url


def verify_webhook_event(payload: bytes, sig_header: str) -> dict:
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )
